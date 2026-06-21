"""F400 시세 서비스. 시세 캐시(TTL)·외부 장애 폴백·등락률·시가총액 계산을 담당한다."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Quote
from .toss import TossClient, TossError

_provider = None

# 토스 캔들은 종목당 단건 호출이라 동시성을 높이면 레이트리밋에 걸려 오히려 실패가 늘어난다
# (관측: 8워커→성공 22/37, 16워커→10/37). 낮게 유지하고 부족분은 sync_daily 재시도로 메운다.
_CANDLE_WORKERS = 4


def market_provider():
    global _provider
    if _provider is None:
        _provider = TossClient()
    return _provider


def set_provider(provider):
    """테스트/대체 구현 주입용 (None 이면 다음 호출에서 실제 클라이언트 재생성)."""
    global _provider
    _provider = provider


def _ttl_seconds():
    return getattr(settings, "TOSS_QUOTE_TTL_SECONDS", 30)


def _dec(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _money(value):
    """Decimal → 문자열. 불필요한 소수점 0 제거(72000.0000→'72000', 185.7000→'185.7')."""
    if value is None:
        return None
    s = format(value, "f")  # 고정소수점(지수표기 방지)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def _is_fresh(quote):
    return (
        quote is not None
        and quote.last_price is not None
        and (timezone.now() - quote.updated_at).total_seconds() < _ttl_seconds()
    )


def refresh_prices(stocks):
    """현재가를 배치로 강제 갱신. 성공 True / 외부 실패 False(기존값 유지=폴백)."""
    stocks = list(stocks)
    if not stocks:
        return True
    try:
        prices = market_provider().get_prices([s.code for s in stocks])
    except TossError:
        return False
    by_code = {s.code: s for s in stocks}
    for code, payload in prices.items():
        stock = by_code.get(code)
        if stock is None:
            continue
        quote, _ = Quote.objects.get_or_create(stock=stock)
        quote.last_price = _dec(payload.get("lastPrice"))
        ts = payload.get("timestamp")
        if ts:
            quote.as_of = parse_datetime(ts)
        quote.save()
    return True


def ensure_fresh_prices(stocks):
    """TTL 지난 종목만 골라 갱신. 반환: 외부 호출이 시도됐고 실패했는지(True=지연표시)."""
    stocks = list(stocks)
    if not stocks:
        return False
    quotes = {q.stock_id: q for q in Quote.objects.filter(stock__in=stocks)}
    stale = [s for s in stocks if not _is_fresh(quotes.get(s.id))]
    if not stale:
        return False
    return not refresh_prices(stale)


def fetch_candles_batch(stocks, interval="1d", count=2):
    """여러 종목의 캔들을 배치로 받아 ``{stock.id: candles}`` 반환(캔들은 최신순 리스트).

    토스 캔들은 종목당 단건 호출이라, 첫 종목을 동기로 받아 토큰을 캐시에 올린 뒤 나머지를
    낮은 동시성(`_CANDLE_WORKERS`)으로 병렬 호출한다(레이트리밋·토큰 동시 재발급 방지).
    전송 실패(TossError)한 종목은 결과에서 빠진다(빈 응답 ``[]`` 과 구분). 시세 등락률용
    일봉(F400)·지표 계산용 장기 일봉(F300)이 공유한다.
    """
    stocks = list(stocks)
    if not stocks:
        return {}
    provider = market_provider()

    def _fetch(stock):
        try:
            return stock.id, provider.get_candles(stock.code, interval, count)
        except TossError:
            return stock.id, None

    results = [_fetch(stocks[0])]
    if len(stocks) > 1:
        with ThreadPoolExecutor(max_workers=min(_CANDLE_WORKERS, len(stocks) - 1)) as pool:
            results.extend(pool.map(_fetch, stocks[1:]))
    return {sid: candles for sid, candles in results if candles is not None}


def ensure_daily_candles(stocks):
    """전일종가·당일거래량(일봉)을 채운다. 종목당 하루 1회만 외부 호출(오늘치 있으면 생략).

    목록(F401 등락률 표시)·상세(F404) 공통. 아침마다 ``manage.py sync_daily`` 로 미리
    채워 두면 첫 요청도 외부 호출 없이 빠르다.
    """
    stocks = list(stocks)
    if not stocks:
        return
    today = timezone.localdate()
    quotes = {q.stock_id: q for q in Quote.objects.filter(stock__in=stocks)}

    def _has_today(stock):
        # daily_as_of 가 오늘이면 '오늘 이미 시도함'. 토스에 일봉이 없어 prev_close 가 비는
        # 종목까지 매 요청 재호출하지 않도록, 성공·빈응답 모두 오늘로 기록한다(전송 실패는 제외).
        q = quotes.get(stock.id)
        return q is not None and q.daily_as_of == today

    stale = [s for s in stocks if not _has_today(s)]
    if not stale:
        return

    fetched = fetch_candles_batch(stale, "1d", 2)  # {id: candles}, 전송 실패 종목은 빠짐
    for stock in stale:
        if stock.id not in fetched:
            continue  # 전송 실패 → 오늘로 표시하지 않고 다음 요청에서 재시도
        candles = fetched[stock.id]
        quote = quotes.get(stock.id)
        if quote is None:
            quote, _ = Quote.objects.get_or_create(stock=stock)
        if candles:  # 빈 응답이면 값은 그대로 두고 '오늘 시도함'만 기록
            quote.volume = _dec(candles[0].get("volume"))
            if len(candles) >= 2:
                quote.prev_close = _dec(candles[1].get("closePrice"))
        quote.daily_as_of = today
        quote.save()


def ensure_shares_outstanding(stocks):
    """발행주식수(시가총액 계산용)가 비어 있는 종목을 토스 종목정보로 한 번에 채운다.

    ``get_stocks`` 는 다건(최대 200) 배치라 유니버스 전체도 한 번의 호출로 끝난다.
    """
    missing = [s for s in stocks if s.shares_outstanding is None]
    if not missing:
        return
    try:
        info = market_provider().get_stocks([s.code for s in missing])
    except TossError:
        return  # 폴백: 다음 기회에
    for stock in missing:
        data = info.get(stock.code)
        if not data or not data.get("sharesOutstanding"):
            continue
        try:
            stock.shares_outstanding = int(Decimal(str(data["sharesOutstanding"])))
            stock.save(update_fields=["shares_outstanding"])
        except (InvalidOperation, ValueError):
            pass


def ensure_daily(stock):
    """상세용: 전일종가·거래량(일봉) + 발행주식수(시총 계산용)를 채운다."""
    ensure_daily_candles([stock])
    ensure_shares_outstanding([stock])
    return Quote.objects.filter(stock=stock).first()


# --- 표시 포맷 / 직렬화 ---
def _direction(rate):
    if rate is None:
        return None
    if rate > 0:
        return "UP"
    if rate < 0:
        return "DOWN"
    return "FLAT"


def format_market_cap(value):
    """원 단위 정수 → '조/억' 표시 문자열."""
    if value is None:
        return None
    won = int(value)
    jo, rest = divmod(won, 10**12)
    eok = rest // 10**8
    parts = []
    if jo:
        parts.append(f"{jo:,}조")
    parts.append(f"{eok:,}억")
    return " ".join(parts)


def _rate_out(rate):
    return float(round(rate, 6)) if rate is not None else None


def serialize_list_item(stock, quote):
    rate = quote.change_rate if quote else None
    price = quote.last_price if quote and quote.last_price is not None else None
    return {
        "code": stock.code,
        "name": stock.name,
        "market": stock.market,
        "sector": stock.sector.name if stock.sector else None,
        "price": _money(price),
        "change_rate": _rate_out(rate),
        "change_direction": _direction(rate),
    }


def serialize_detail(stock, quote, delayed=False):
    rate = quote.change_rate if quote else None
    price = quote.last_price if quote and quote.last_price is not None else None
    market_cap = None
    if price is not None and stock.shares_outstanding:
        market_cap = int(price * stock.shares_outstanding)
    return {
        "code": stock.code,
        "name": stock.name,
        "market": stock.market,
        "sector": stock.sector.name if stock.sector else "미분류",
        "price": _money(price),
        "prev_close": _money(quote.prev_close) if quote else None,
        "change_rate": _rate_out(rate),
        "change_direction": _direction(rate),
        "volume": _money(quote.volume) if quote else None,
        "market_cap": market_cap,
        "market_cap_display": format_market_cap(market_cap),
        "as_of": quote.as_of.isoformat() if quote and quote.as_of else None,
        "is_delayed": delayed,  # 외부 호출 실패로 마지막 정상값 표시 중(F404 지연표시)
        "news": [],  # F500(뉴스)에서 채움 — 현재 보류
    }
