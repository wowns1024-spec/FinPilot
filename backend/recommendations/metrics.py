"""F300 시세 파생 지표(변동성·모멘텀·유동성) 계산·저장.

토스가 펀더멘털을 안 주므로, 일봉 history 를 배치로 받아(`stocks.services.fetch_candles_batch`)
지표를 계산하고 StockMetric 스냅샷에 저장한다. `compute_metrics` 관리 커맨드가 호출한다.
"""

import statistics

from django.conf import settings
from django.utils import timezone

from stocks import services as stock_services

from .models import StockMetric


def _to_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metrics_from_candles(candles):
    """캔들(최신순)에서 (volatility, momentum, liquidity, window) 계산. 부족하면 None.

    - volatility: 일간수익률 표준편차(클수록 변동성↑)
    - momentum: 기간수익률 = (최근종가 - 가장 오래된 종가) / 오래된 종가
    - liquidity: 평균 일거래대금 = mean(종가 × 거래량)
    """
    closes = [v for v in (_to_float(c.get("closePrice")) for c in candles) if v is not None]
    if len(closes) < 2:
        return None

    # 일간수익률(최신순 리스트라 i 가 i+1 보다 최근): r = (closes[i] - closes[i+1]) / closes[i+1]
    returns = [
        (closes[i] - closes[i + 1]) / closes[i + 1]
        for i in range(len(closes) - 1)
        if closes[i + 1]
    ]
    volatility = statistics.pstdev(returns) if len(returns) >= 2 else None

    oldest = closes[-1]
    momentum = (closes[0] - oldest) / oldest if oldest else None

    turnovers = []
    for c in candles:
        cp, vol = _to_float(c.get("closePrice")), _to_float(c.get("volume"))
        if cp is not None and vol is not None:
            turnovers.append(cp * vol)
    liquidity = statistics.mean(turnovers) if turnovers else None

    return volatility, momentum, liquidity, len(closes)


def compute_metrics(stocks, window=None):
    """종목들의 일봉을 받아 지표를 계산하고 StockMetric upsert. 갱신된 종목 수 반환.

    캔들이 비거나(데이터 없음) 전송 실패한 종목은 건너뛴다(커맨드가 재시도).
    """
    stocks = list(stocks)
    if not stocks:
        return 0
    window = window or getattr(settings, "METRIC_WINDOW", 60)
    today = timezone.localdate()
    fetched = stock_services.fetch_candles_batch(stocks, "1d", window)

    updated = 0
    for stock in stocks:
        candles = fetched.get(stock.id)
        if not candles:
            continue
        computed = metrics_from_candles(candles)
        if computed is None:
            continue
        volatility, momentum, liquidity, n = computed
        StockMetric.objects.update_or_create(
            stock=stock,
            defaults={
                "volatility": volatility,
                "momentum": momentum,
                "liquidity": liquidity,
                "window": n,
                "as_of": today,
            },
        )
        updated += 1
    return updated
