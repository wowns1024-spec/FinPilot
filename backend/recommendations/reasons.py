"""규칙 기반 추천 이유 템플릿(F300). GMS 미설정/실패 시 폴백으로 쓴다."""


def _pct(x):
    return f"{x * 100:+.1f}%"


def template_reason(profile, stock, metric, breakdown):
    """점수 구성요소(breakdown)와 지표(metric)에서 핵심 근거만 골라 한 문장으로."""
    parts = []
    if breakdown.get("sector_match", 0) >= 1.0 and stock.sector:
        parts.append(f"회원님이 선택한 ‘{stock.sector.name}’ 산업")
    if breakdown.get("risk_fit", 0) >= 0.7:
        parts.append(f"{profile.get_risk_type_display()} 성향에 맞는 변동성")
    if metric and metric.momentum is not None:
        if metric.momentum >= 0.03:
            parts.append(f"최근 상승 흐름({_pct(metric.momentum)})")
        elif metric.momentum <= -0.03:
            parts.append(f"최근 조정 구간({_pct(metric.momentum)})")
    if breakdown.get("liquidity", 0) >= 0.7:
        parts.append("풍부한 거래량")
    if not parts:
        parts.append("투자 성향과의 종합 적합도")
    return f"{stock.name}은(는) " + ", ".join(parts) + " 측면에서 추천됩니다."
