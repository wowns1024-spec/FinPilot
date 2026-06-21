"""F300 규칙 기반 스코어링.

각 후보 종목을 사용자 프로필에 대해 채점한다::

    score = w_sector·매치 + w_risk·성향적합 + w_momentum·모멘텀 + w_liquidity·유동성

지표(변동성·모멘텀·유동성)는 후보군 내 min-max 정규화 후 사용한다. 지표가 없으면
중립(0.5)으로 둬, compute_metrics 전에도 관심산업 매치 위주로 동작한다.
"""

# 위험성향별 '선호 변동성' 목표(정규화 0~1). 안정형=저변동, 공격형=고변동.
RISK_VOL_TARGET = {
    "STABLE": 0.10,
    "STABLE_SEEKING": 0.30,
    "BALANCED": 0.50,
    "ACTIVE": 0.70,
    "AGGRESSIVE": 0.90,
}

_BASE_WEIGHTS = {"sector": 0.35, "risk": 0.30, "momentum": 0.20, "liquidity": 0.15}


def weights_for(profile):
    """프로필(투자목적·기간)에 따라 가중치를 조정하고 합이 1이 되도록 정규화."""
    w = dict(_BASE_WEIGHTS)

    goal = profile.investment_goal
    if goal in ("GROWTH", "SHORT_TERM_GAIN"):  # 성장·단기차익 → 모멘텀↑
        w["momentum"] += 0.10
        w["risk"] -= 0.05
        w["liquidity"] -= 0.05
    elif goal in ("STABLE_INCOME", "DIVIDEND", "RETIREMENT"):  # 안정·배당·노후 → 안정성↑
        w["momentum"] -= 0.10
        w["risk"] += 0.05
        w["liquidity"] += 0.05

    period = profile.investment_period
    if period == "SHORT":  # 단타 → 모멘텀·유동성↑, 산업선호 비중↓
        w["momentum"] += 0.05
        w["liquidity"] += 0.05
        w["sector"] -= 0.10
    elif period == "LONG":  # 중장기 → 산업선호↑, 모멘텀↓
        w["sector"] += 0.05
        w["momentum"] -= 0.05

    w = {k: max(v, 0.0) for k, v in w.items()}
    total = sum(w.values()) or 1.0
    return {k: v / total for k, v in w.items()}


def _normalize(values):
    """값 리스트 → 0~1 (min-max). None 은 0.5(중립). 모두 같거나 비면 전부 0.5."""
    nums = [v for v in values if v is not None]
    if not nums:
        return [0.5] * len(values)
    lo, hi = min(nums), max(nums)
    span = hi - lo
    if span == 0:
        return [0.5] * len(values)
    return [0.5 if v is None else (v - lo) / span for v in values]


def score_candidates(profile, candidates):
    """``candidates``: [(stock, metric_or_None), ...]

    반환: 점수 내림차순 [(stock, metric, score(0~100), breakdown(0~1 dict))].
    """
    candidates = list(candidates)
    if not candidates:
        return []

    nvol = _normalize([m.volatility if m else None for _, m in candidates])
    nmom = _normalize([m.momentum if m else None for _, m in candidates])
    nliq = _normalize([m.liquidity if m else None for _, m in candidates])

    weights = weights_for(profile)
    target = RISK_VOL_TARGET.get(profile.risk_type, 0.5)
    sector_ids = set(profile.sectors.values_list("id", flat=True))

    scored = []
    for i, (stock, metric) in enumerate(candidates):
        comp = {
            "sector_match": 1.0 if stock.sector_id in sector_ids else 0.0,
            "risk_fit": 1.0 - abs(nvol[i] - target),
            "momentum": nmom[i],
            "liquidity": nliq[i],
        }
        score01 = (
            weights["sector"] * comp["sector_match"]
            + weights["risk"] * comp["risk_fit"]
            + weights["momentum"] * comp["momentum"]
            + weights["liquidity"] * comp["liquidity"]
        )
        scored.append((stock, metric, round(score01 * 100, 1), comp))

    scored.sort(key=lambda r: r[2], reverse=True)
    return scored
