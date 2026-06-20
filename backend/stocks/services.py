import json
import re
import time
from decimal import Decimal, InvalidOperation
from urllib import parse, request
from urllib.error import HTTPError, URLError

from django.conf import settings


STOCK_UNIVERSE = [
    ("005930", "삼성전자", "KOSPI", "반도체"),
    ("000660", "SK하이닉스", "KOSPI", "반도체"),
    ("373220", "LG에너지솔루션", "KOSPI", "2차전지"),
    ("012450", "한화에어로스페이스", "KOSPI", "방산"),
    ("035420", "NAVER", "KOSPI", "AI"),
    ("015760", "한국전력", "KOSPI", "에너지"),
    ("259960", "크래프톤", "KOSPI", "게임"),
    ("207940", "삼성바이오로직스", "KOSPI", "바이오"),
    ("005380", "현대차", "KOSPI", "자동차"),
    ("105560", "KB금융", "KOSPI", "금융"),
    ("035720", "카카오", "KOSPI", "플랫폼"),
    ("068270", "셀트리온", "KOSPI", "바이오"),
    ("005490", "POSCO홀딩스", "KOSPI", "철강"),
    ("006400", "삼성SDI", "KOSPI", "2차전지"),
    ("051910", "LG화학", "KOSPI", "화학"),
    ("000270", "기아", "KOSPI", "자동차"),
    ("028260", "삼성물산", "KOSPI", "지주사"),
    ("055550", "신한지주", "KOSPI", "금융"),
    ("086790", "하나금융지주", "KOSPI", "금융"),
    ("323410", "카카오뱅크", "KOSPI", "금융"),
    ("247540", "에코프로비엠", "KOSDAQ", "2차전지"),
    ("086520", "에코프로", "KOSDAQ", "2차전지"),
    ("196170", "알테오젠", "KOSDAQ", "바이오"),
    ("042660", "한화오션", "KOSPI", "조선"),
    ("010140", "삼성중공업", "KOSPI", "조선"),
    ("329180", "HD현대중공업", "KOSPI", "조선"),
    ("064350", "현대로템", "KOSPI", "방산"),
    ("011200", "HMM", "KOSPI", "해운"),
    ("003550", "LG", "KOSPI", "지주사"),
    ("034020", "두산에너빌리티", "KOSPI", "에너지"),
    ("AAPL", "애플", "NASDAQ", "IT"),
    ("MSFT", "마이크로소프트", "NASDAQ", "IT"),
    ("NVDA", "엔비디아", "NASDAQ", "반도체"),
    ("TSLA", "테슬라", "NASDAQ", "자동차"),
]

STOCK_DIRECTORY = [
    {
        "symbol": symbol,
        "name": name,
        "market": market,
        "sector": sector,
        "current_price": 0,
        "change_rate": None,
        "market_cap": 0,
        "news_title": f"{name} 관련 시장 흐름을 확인해 보세요.",
    }
    for symbol, name, market, sector in STOCK_UNIVERSE
]

_TOKEN_CACHE = {"access_token": "", "expires_at": 0}
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9.\-]+$")


def decimal_to_float(value):
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return None


def toss_config_status():
    has_access_token = bool(settings.TOSS_ACCESS_TOKEN)
    has_client_id = bool(settings.TOSS_CLIENT_ID)
    has_client_secret = bool(settings.TOSS_CLIENT_SECRET)
    configured = has_access_token or (has_client_id and has_client_secret)

    if configured:
        message = "토스증권 API 인증 설정이 준비되었습니다."
    elif has_client_secret and not has_client_id:
        message = "TOSS_CLIENT_SECRET은 있지만 TOSS_CLIENT_ID가 없어 토큰을 발급할 수 없습니다."
    else:
        message = "TOSS_CLIENT_ID와 TOSS_CLIENT_SECRET을 .env에 설정해야 합니다."

    return {
        "configured": configured,
        "has_access_token": has_access_token,
        "has_client_id": has_client_id,
        "has_client_secret": has_client_secret,
        "message": message,
    }


def toss_configured():
    return toss_config_status()["configured"]


def get_toss_access_token():
    if settings.TOSS_ACCESS_TOKEN:
        return settings.TOSS_ACCESS_TOKEN

    now = time.time()
    if _TOKEN_CACHE["access_token"] and _TOKEN_CACHE["expires_at"] > now + 60:
        return _TOKEN_CACHE["access_token"]

    if not settings.TOSS_CLIENT_ID or not settings.TOSS_CLIENT_SECRET:
        return ""

    data = parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": settings.TOSS_CLIENT_ID,
            "client_secret": settings.TOSS_CLIENT_SECRET,
        }
    ).encode("utf-8")
    req = request.Request(
        f"{settings.TOSS_API_BASE_URL}/oauth2/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=8) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, OSError, URLError, TimeoutError, json.JSONDecodeError):
        return ""

    access_token = body.get("access_token", "")
    expires_in = int(body.get("expires_in", 0) or 0)
    _TOKEN_CACHE["access_token"] = access_token
    _TOKEN_CACHE["expires_at"] = now + expires_in
    return access_token


def toss_get(path, params):
    token = get_toss_access_token()
    if not token:
        return None

    query = parse.urlencode(params)
    req = request.Request(
        f"{settings.TOSS_API_BASE_URL}{path}?{query}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=8) as response:
            return json.loads(response.read().decode("utf-8")).get("result")
    except (HTTPError, OSError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def get_toss_prices(symbols):
    symbols = [symbol for symbol in symbols if symbol]
    if not symbols:
        return {}
    result = toss_get("/api/v1/prices", {"symbols": ",".join(symbols)})
    if not isinstance(result, list):
        return {}
    return {item["symbol"]: item for item in result if item.get("symbol")}


def get_toss_stock_infos(symbols):
    symbols = [symbol for symbol in symbols if symbol]
    if not symbols:
        return {}
    result = toss_get("/api/v1/stocks", {"symbols": ",".join(symbols)})
    if not isinstance(result, list):
        return {}
    return {item["symbol"]: item for item in result if item.get("symbol")}


def get_toss_daily_candles(symbol):
    result = toss_get(
        "/api/v1/candles",
        {"symbol": symbol, "interval": "1d", "count": 2, "adjusted": "true"},
    )
    if not isinstance(result, dict):
        return []
    candles = result.get("candles")
    return candles if isinstance(candles, list) else []


def get_toss_candle_metrics(symbols):
    metrics = {}
    for symbol in symbols:
        candles = get_toss_daily_candles(symbol)
        if len(candles) < 2:
            continue

        latest = candles[0]
        previous = candles[1]
        latest_close = decimal_to_float(latest.get("closePrice"))
        previous_close = decimal_to_float(previous.get("closePrice"))
        if latest_close is None or not previous_close:
            continue

        metrics[symbol] = {
            "close_price": latest_close,
            "change_rate": round(((latest_close - previous_close) / previous_close) * 100, 2),
            "timestamp": latest.get("timestamp"),
            "currency": latest.get("currency", "KRW"),
        }
    return metrics


def normalize_symbol(query):
    return (query or "").strip().upper()


def is_symbol_query(query):
    symbol = normalize_symbol(query)
    return bool(symbol) and bool(SYMBOL_PATTERN.match(symbol))


def find_local_stock(symbol):
    return next((item for item in STOCK_DIRECTORY if item["symbol"] == symbol), None)


def make_stock_from_toss(symbol, info=None):
    local = find_local_stock(symbol)
    if local:
        return local
    return {
        "symbol": symbol,
        "name": (info or {}).get("name") or symbol,
        "market": (info or {}).get("market") or "-",
        "sector": "기타",
        "current_price": 0,
        "change_rate": None,
        "market_cap": 0,
        "news_title": f"{(info or {}).get('name') or symbol} 관련 시장 흐름을 확인해 보세요.",
    }


def normalize_stock(stock, price=None, info=None, candle=None):
    current_price = decimal_to_float((price or {}).get("lastPrice"))
    if current_price is None and candle:
        current_price = candle.get("close_price")
    if current_price is None:
        current_price = stock["current_price"]

    change_rate = None
    if candle:
        change_rate = candle.get("change_rate")
    if change_rate is None:
        change_rate = stock["change_rate"]

    market_cap = stock["market_cap"]
    shares = decimal_to_float((info or {}).get("sharesOutstanding"))
    if shares and current_price:
        market_cap = round(shares * current_price)

    return {
        "symbol": stock["symbol"],
        "name": (info or {}).get("name") or stock["name"],
        "market": (info or {}).get("market") or stock["market"],
        "sector": stock["sector"],
        "current_price": current_price,
        "currency": (price or info or candle or {}).get("currency", "KRW"),
        "price_timestamp": (price or {}).get("timestamp") or (candle or {}).get("timestamp"),
        "change_rate": change_rate,
        "market_cap": market_cap,
        "news_title": stock["news_title"],
        "data_source": "toss" if price or info or candle else "fallback",
    }


def filter_local_stocks(query):
    query = (query or "").strip().lower()
    if not query:
        return STOCK_DIRECTORY
    return [
        stock
        for stock in STOCK_DIRECTORY
        if query in stock["name"].lower() or query in stock["symbol"].lower()
    ]


def list_stocks(query="", limit=30):
    query = (query or "").strip()
    stocks = filter_local_stocks(query)[:limit]

    # 토스 Open API는 종목명 검색이 없으므로, 코드/티커 검색은 직접 조회한다.
    if query and not stocks and is_symbol_query(query):
        symbol = normalize_symbol(query)
        infos = get_toss_stock_infos([symbol])
        info = infos.get(symbol)
        if info:
            stocks = [make_stock_from_toss(symbol, info)]

    symbols = [stock["symbol"] for stock in stocks]
    prices = get_toss_prices(symbols)
    infos = get_toss_stock_infos(symbols)
    candle_metrics = get_toss_candle_metrics(symbols)
    return [
        normalize_stock(
            stock,
            price=prices.get(stock["symbol"]),
            info=infos.get(stock["symbol"]),
            candle=candle_metrics.get(stock["symbol"]),
        )
        for stock in stocks
    ]


def get_stock_detail(symbol):
    symbol = normalize_symbol(symbol)
    prices = get_toss_prices([symbol])
    infos = get_toss_stock_infos([symbol])
    candle_metrics = get_toss_candle_metrics([symbol])
    info = infos.get(symbol)
    stock = make_stock_from_toss(symbol, info)

    if not info and not find_local_stock(symbol):
        return None

    detail = normalize_stock(
        stock,
        price=prices.get(symbol),
        info=info,
        candle=candle_metrics.get(symbol),
    )
    detail["related_news"] = [
        {
            "title": detail["news_title"],
            "source": "FinPilot",
            "url": f"/news?symbol={symbol}",
        }
    ]
    detail["description"] = (
        f"{detail['name']}는 {detail['sector']} 산업군에 속한 "
        f"{detail['market']} 상장 종목입니다."
    )
    return detail
