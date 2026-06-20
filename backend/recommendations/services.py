import json
import re
from http.client import IncompleteRead
from urllib import request
from urllib.error import HTTPError, URLError

from django.conf import settings

from investments.choices import INTEREST_INDUSTRY_CHOICES


STOCK_UNIVERSE = [
    {
        "stock_name": "삼성전자",
        "stock_code": "005930",
        "sector": "semiconductor",
        "current_price": 72800,
        "risk": 45,
        "market_interest": 92,
        "style_tags": ["value", "dividend"],
        "period_tags": ["swing", "long"],
        "news_title": "반도체 업황 회복 기대감 지속",
        "news_url": "/news?sector=semiconductor",
    },
    {
        "stock_name": "SK하이닉스",
        "stock_code": "000660",
        "sector": "semiconductor",
        "current_price": 88700,
        "risk": 62,
        "market_interest": 94,
        "style_tags": ["growth", "momentum"],
        "period_tags": ["swing", "long"],
        "news_title": "AI 메모리 수요 증가 관련 기대감",
        "news_url": "/news?sector=semiconductor",
    },
    {
        "stock_name": "LG에너지솔루션",
        "stock_code": "373220",
        "sector": "battery",
        "current_price": 352000,
        "risk": 70,
        "market_interest": 83,
        "style_tags": ["growth"],
        "period_tags": ["long"],
        "news_title": "2차전지 수요 회복 여부 주목",
        "news_url": "/news?sector=battery",
    },
    {
        "stock_name": "한화에어로스페이스",
        "stock_code": "012450",
        "sector": "defense",
        "current_price": 185400,
        "risk": 66,
        "market_interest": 88,
        "style_tags": ["growth", "momentum"],
        "period_tags": ["swing", "long"],
        "news_title": "방산 수출 모멘텀 확대 기대",
        "news_url": "/news?sector=defense",
    },
    {
        "stock_name": "NAVER",
        "stock_code": "035420",
        "sector": "ai",
        "current_price": 187500,
        "risk": 58,
        "market_interest": 80,
        "style_tags": ["growth", "news"],
        "period_tags": ["swing", "long"],
        "news_title": "AI 서비스 고도화와 광고 회복 기대",
        "news_url": "/news?sector=ai",
    },
    {
        "stock_name": "한국전력",
        "stock_code": "015760",
        "sector": "energy",
        "current_price": 22950,
        "risk": 42,
        "market_interest": 64,
        "style_tags": ["value"],
        "period_tags": ["long"],
        "news_title": "전력 수요와 요금 정상화 흐름 주목",
        "news_url": "/news?sector=energy",
    },
    {
        "stock_name": "크래프톤",
        "stock_code": "259960",
        "sector": "game",
        "current_price": 268000,
        "risk": 63,
        "market_interest": 73,
        "style_tags": ["growth"],
        "period_tags": ["swing", "long"],
        "news_title": "신작 출시와 글로벌 매출 흐름 주목",
        "news_url": "/news?sector=game",
    },
    {
        "stock_name": "삼성바이오로직스",
        "stock_code": "207940",
        "sector": "bio",
        "current_price": 782000,
        "risk": 55,
        "market_interest": 76,
        "style_tags": ["growth", "value"],
        "period_tags": ["long"],
        "news_title": "위탁생산 수주 확대 기대",
        "news_url": "/news?sector=bio",
    },
    {
        "stock_name": "현대차",
        "stock_code": "005380",
        "sector": "auto",
        "current_price": 209000,
        "risk": 48,
        "market_interest": 79,
        "style_tags": ["value", "dividend"],
        "period_tags": ["swing", "long"],
        "news_title": "전기차 전환과 주주환원 정책 주목",
        "news_url": "/news?sector=auto",
    },
    {
        "stock_name": "KB금융",
        "stock_code": "105560",
        "sector": "finance",
        "current_price": 72400,
        "risk": 39,
        "market_interest": 70,
        "style_tags": ["dividend", "value"],
        "period_tags": ["long"],
        "news_title": "배당 매력과 금리 환경 변화 점검",
        "news_url": "/news?sector=finance",
    },
]

RISK_TARGET = {
    "stable": 30,
    "stability_seeking": 42,
    "balanced": 55,
    "active": 68,
    "aggressive": 82,
}

GOAL_STYLE_BONUS = {
    "growth": ["growth", "momentum"],
    "stable_income": ["value", "dividend"],
    "dividend": ["dividend"],
    "short_profit": ["momentum", "news"],
    "retirement": ["value", "dividend"],
}


def _label(mapping, value):
    return mapping.get(value, value)


def build_profile_snapshot(profile):
    return {
        "available_asset": profile.available_asset,
        "risk_type": profile.risk_type,
        "risk_type_label": profile.get_risk_type_display(),
        "investment_period": profile.investment_period,
        "investment_period_label": profile.get_investment_period_display(),
        "investment_goal": profile.investment_goal,
        "investment_goal_label": profile.get_investment_goal_display(),
        "investment_style": profile.investment_style,
        "investment_style_label": profile.get_investment_style_display(),
        "interest_industries": profile.interest_industries,
        "interest_industry_labels": [
            _label(INTEREST_INDUSTRY_CHOICES, value)
            for value in profile.interest_industries
        ],
    }


def build_analysis_summary(profile):
    industries = ", ".join(
        _label(INTEREST_INDUSTRY_CHOICES, value)
        for value in profile.interest_industries
    )
    style = profile.get_investment_style_display() or "특정 스타일 미선택"
    return (
        f"{profile.get_risk_type_display()} 성향, "
        f"{profile.get_investment_period_display()} 투자 기간, "
        f"{profile.get_investment_goal_display()} 목적, "
        f"{style} 기준으로 {industries} 섹터를 우선 분석했습니다."
    )


def score_stock(profile, stock):
    target_risk = RISK_TARGET.get(profile.risk_type, 55)
    risk_score = max(0, 100 - abs(stock["risk"] - target_risk) * 2)
    industry_score = 100 if stock["sector"] in profile.interest_industries else 45
    period_score = 100 if profile.investment_period in stock["period_tags"] else 60

    preferred_styles = set(GOAL_STYLE_BONUS.get(profile.investment_goal, []))
    if profile.investment_style:
        preferred_styles.add(profile.investment_style)
    style_score = 100 if preferred_styles.intersection(stock["style_tags"]) else 55

    score = (
        risk_score * 0.30
        + industry_score * 0.30
        + stock["market_interest"] * 0.20
        + period_score * 0.10
        + style_score * 0.10
    )
    return round(max(0, min(100, score)))


def fallback_reason(profile, stock):
    sector = _label(INTEREST_INDUSTRY_CHOICES, stock["sector"])
    matched = stock["sector"] in profile.interest_industries
    industry_phrase = (
        f"관심 산업인 {sector} 섹터와 직접 연결됩니다."
        if matched
        else f"{sector} 섹터의 시장 관심도가 높아 보조 후보로 선별했습니다."
    )
    return (
        f"{stock['stock_name']}은 {profile.get_risk_type_display()} 성향과 "
        f"{profile.get_investment_period_display()} 투자 기간을 고려했을 때 "
        f"변동성과 시장 관심도의 균형이 적절한 후보입니다. "
        f"{industry_phrase} 최근 흐름은 '{stock['news_title']}'를 중심으로 확인할 수 있습니다."
    )


def parse_gms_json_response(body):
    """GMS 응답이 감싼 JSON/문자열 JSON 어느 쪽이어도 추천 목록을 꺼낸다."""
    if isinstance(body, list):
        return body

    if not isinstance(body, dict):
        return []

    for key in ("recommendations", "items", "stocks", "results"):
        value = body.get(key)
        if isinstance(value, list):
            return value

    content = (
        body.get("output_text")
        or body.get("content")
        or body.get("text")
        or body.get("message")
    )
    if isinstance(content, str):
        try:
            decoded = json.loads(content)
        except json.JSONDecodeError:
            return []
        return parse_gms_json_response(decoded)

    output = body.get("output")
    if isinstance(output, list):
        text_parts = []
        for output_item in output:
            for content_item in output_item.get("content", []):
                text = content_item.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
        if text_parts:
            try:
                decoded = json.loads("".join(text_parts))
            except json.JSONDecodeError:
                return []
            return parse_gms_json_response(decoded)

    return []


def decode_gms_response(raw):
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    matches = re.findall(r'"text"\s*:\s*"((?:\\.|[^"\\])*)"', text)
    if not matches:
        return None

    decoded_parts = []
    for match in matches:
        try:
            decoded_parts.append(json.loads(f'"{match}"'))
        except json.JSONDecodeError:
            continue
    if not decoded_parts:
        return None
    return {"output_text": "".join(decoded_parts)}


def post_gms(input_payload):
    if not settings.GMS_API_KEY or not settings.GMS_API_URL:
        return None

    payload = {
        "model": settings.GMS_MODEL,
        "input": [
            {
                "role": "system",
                "content": (
                    "당신은 한국 주식 추천을 돕는 AI입니다. "
                    "투자 조언 단정 대신 사용자의 투자성향에 맞는 후보와 근거를 JSON으로 제공합니다."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(input_payload, ensure_ascii=False),
            },
        ],
        "text": {"format": {"type": "json_object"}},
        "temperature": 0.2,
        "max_output_tokens": 1200,
        "store": False,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        settings.GMS_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.GMS_API_KEY}",
            "Accept-Encoding": "identity",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            try:
                raw = response.read()
            except IncompleteRead as exc:
                raw = exc.partial
            return decode_gms_response(raw)
    except (HTTPError, OSError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def find_stock_by_code_or_name(item):
    code = str(item.get("stock_code") or item.get("code") or "").strip()
    name = str(item.get("stock_name") or item.get("name") or "").strip()
    for stock in STOCK_UNIVERSE:
        if code and stock["stock_code"] == code:
            return stock
        if name and stock["stock_name"] == name:
            return stock
    return None


def normalize_gms_item(profile, item, rank):
    stock = find_stock_by_code_or_name(item)
    stock_name = item.get("stock_name") or item.get("name") or (stock or {}).get("stock_name")
    stock_code = item.get("stock_code") or item.get("code") or (stock or {}).get("stock_code")

    if not stock_name or not stock_code:
        return None

    sector = item.get("sector") or (stock or {}).get("sector") or "기타"
    if sector in INTEREST_INDUSTRY_CHOICES:
        sector = _label(INTEREST_INDUSTRY_CHOICES, sector)

    score = item.get("score") or item.get("recommendation_score")
    try:
        score = round(float(score))
    except (TypeError, ValueError):
        score = score_stock(profile, stock) if stock else 70

    current_price = item.get("current_price") or item.get("price")
    try:
        current_price = int(str(current_price).replace(",", ""))
    except (TypeError, ValueError):
        current_price = (stock or {}).get("current_price", 0)

    reason = item.get("reason") or item.get("recommendation_reason")
    if not reason:
        reason = fallback_reason(profile, stock) if stock else "투자 성향과 관심 산업을 기준으로 AI가 선별한 추천 후보입니다."

    return {
        "rank": rank,
        "stock_name": str(stock_name),
        "stock_code": str(stock_code),
        "sector": str(sector),
        "current_price": current_price,
        "score": max(0, min(100, score)),
        "reason": str(reason),
        "news_title": item.get("news_title") or (stock or {}).get("news_title", ""),
        "news_url": item.get("news_url") or (stock or {}).get("news_url", "/news"),
    }


def call_gms_recommendations(profile, limit=5):
    prompt = (
        "사용자의 투자성향 DB 값과 후보 종목을 바탕으로 한국 주식 추천 목록을 생성하세요. "
        "반드시 JSON으로만 답하세요. 형식은 "
        '{"recommendations":[{"stock_name":"","stock_code":"","sector":"","current_price":0,'
        '"score":0,"reason":"","news_title":"","news_url":""}]} 입니다. '
        "score는 100점 기준이며 reason은 한국어 2문장 이내로 작성하세요."
    )
    payload = {
        "task": "stock_recommendation",
        "instruction": prompt,
        "profile": build_profile_snapshot(profile),
        "candidates": [
            {
                "stock_name": stock["stock_name"],
                "stock_code": stock["stock_code"],
                "sector": _label(INTEREST_INDUSTRY_CHOICES, stock["sector"]),
                "current_price": stock["current_price"],
                "risk": stock["risk"],
                "market_interest": stock["market_interest"],
                "style_tags": stock["style_tags"],
                "period_tags": stock["period_tags"],
                "news_title": stock["news_title"],
            }
            for stock in STOCK_UNIVERSE
        ],
        "limit": limit,
    }

    body = post_gms(payload)
    if body is None:
        return [], False

    raw_items = parse_gms_json_response(body)
    normalized = []
    seen_codes = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        normalized_item = normalize_gms_item(profile, item, len(normalized) + 1)
        if normalized_item is None:
            continue
        if normalized_item["stock_code"] in seen_codes:
            continue
        seen_codes.add(normalized_item["stock_code"])
        normalized.append(normalized_item)
        if len(normalized) >= limit:
            break

    return normalized, bool(normalized)


def generate_fallback_recommendations(profile, limit=5):
    ranked = []
    for stock in STOCK_UNIVERSE:
        item = dict(stock)
        item["score"] = score_stock(profile, stock)
        ranked.append(item)

    ranked.sort(key=lambda item: item["score"], reverse=True)
    return [
        {
            "rank": rank,
            "stock_name": stock["stock_name"],
            "stock_code": stock["stock_code"],
            "sector": _label(INTEREST_INDUSTRY_CHOICES, stock["sector"]),
            "current_price": stock["current_price"],
            "score": stock["score"],
            "reason": fallback_reason(profile, stock),
            "news_title": stock["news_title"],
            "news_url": stock["news_url"],
        }
        for rank, stock in enumerate(ranked[:limit], start=1)
    ]


def generate_recommendations(profile, limit=5):
    results, used_ai = call_gms_recommendations(profile, limit=limit)
    if not results:
        results = generate_fallback_recommendations(profile, limit=limit)

    return {
        "analysis_summary": build_analysis_summary(profile),
        "profile_snapshot": build_profile_snapshot(profile),
        "used_ai": used_ai,
        "items": results,
    }
