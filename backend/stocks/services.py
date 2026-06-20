"""F400 시세 서비스. 시세 캐시(TTL)·외부 장애 폴백·등락률·시가총액 계산을 담당한다."""

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Quote
from .toss import TossClient, TossError

_provider = None


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


def ensure_daily(stock):
    """전일종가·당일거래량(candles)과 발행주식수(stocks)를 채운다. 오늘 이미 있으면 생략."""
    quote, _ = Quote.objects.get_or_create(stock=stock)
    today = timezone.localdate()
    if quote.daily_as_of != today or quote.prev_close is None:
        try:
            candles = market_provider().get_candles(stock.code, "1d", 2)
            if candles:
                quote.volume = _dec(candles[0].get("volume"))
                if len(candles) >= 2:
                    quote.prev_close = _dec(candles[1].get("closePrice"))
                quote.daily_as_of = today
                quote.save()
        except TossError:
            pass  # 폴백: 기존값 유지
    if stock.shares_outstanding is None:
        try:
            info = market_provider().get_stocks([stock.code]).get(stock.code)
            if info and info.get("sharesOutstanding"):
                stock.shares_outstanding = int(Decimal(str(info["sharesOutstanding"])))
                stock.save(update_fields=["shares_outstanding"])
        except (TossError, InvalidOperation, ValueError):
            pass
    return quote


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
