"""F300 추천 오케스트레이션: 점수 산정 → 추천 이유 생성 → 영속화/무효화."""

import logging

from django.conf import settings
from django.db import transaction

from profiles.models import InvestmentProfile
from stocks import services as stock_services
from stocks.models import Stock

from . import gms, news, reasons, scoring
from .models import Recommendation, RecommendationItem, StockMetric, StockNewsSummary

logger = logging.getLogger(__name__)
_NEWS_SUMMARY_MAX_CHARS = 800


def active_profile(user):
    return InvestmentProfile.objects.filter(user=user, is_active=True).first()


def invalidate_for_user(user):
    """프로필 변경/삭제 시 기존 활성 추천을 무효화(F300)."""
    Recommendation.objects.filter(user=user, is_active=True).update(is_active=False)


def _pct(value):
    if value is None:
        return "데이터 없음"
    return f"{value * 100:+.1f}%"


def _score_component_text(breakdown):
    labels = {
        "sector_match": "관심산업 일치",
        "risk_fit": "위험성향 적합도",
        "momentum": "기간수익률 점수",
        "liquidity": "유동성 점수",
    }
    parts = []
    for key, label in labels.items():
        value = breakdown.get(key)
        if value is None:
            continue
        parts.append(f"{label} {value * 100:.0f}점")
    return ", ".join(parts) if parts else "세부 점수 데이터 없음"


def _metric_text(metric):
    if not metric:
        return "시세 파생 지표 데이터 없음"
    parts = [
        f"기간수익률(모멘텀) {_pct(metric.momentum)}",
        f"변동성 {_pct(metric.volatility)}",
    ]
    if metric.liquidity is not None:
        parts.append(f"평균 거래대금 {metric.liquidity:,.0f}원")
    return ", ".join(parts)


def _clean_news_summary(summary):
    summary = (summary or "").strip()
    if not summary:
        return "수집된 뉴스 요약 없음"
    if len(summary) > _NEWS_SUMMARY_MAX_CHARS:
        return summary[:_NEWS_SUMMARY_MAX_CHARS].rstrip() + "..."
    return summary


def _news_context_for(stocks):
    summaries = StockNewsSummary.objects.filter(stock__in=stocks).exclude(summary="")
    return (
        {item.stock_id: item.summary for item in summaries},
        {item.stock_id: item.articles for item in summaries},
    )


def _build_prompt(profile, stock, metric, rank, score, breakdown, news_summary=""):
    mom = (
        "데이터 없음"
        if not metric or metric.momentum is None
        else f"{metric.momentum * 100:+.1f}%"
    )
    return (
        "당신은 한국 주식 투자 보조원입니다. 아래 정보를 바탕으로 이 종목을 추천하는 이유를 "
        "1~2문장의 자연스러운 한국어로 작성하세요. 추천 순위, 점수 근거, 뉴스 요약 중 "
        "의미 있는 내용을 반영하되 단정적 표현·투자 권유는 피하고 사실 위주로 쓰세요.\n"
        f"- 종목: {stock.name}({stock.code}), 산업: {stock.sector.name if stock.sector else '미분류'}\n"
        f"- 사용자 위험성향: {profile.get_risk_type_display()}, "
        f"투자기간: {profile.get_investment_period_display()}, "
        f"투자목적: {profile.get_investment_goal_display()}\n"
        f"- 추천 선정 결과: {rank}위, 최종 점수 {score:.1f}점\n"
        f"- 점수 구성: {_score_component_text(breakdown)}\n"
        f"- 관심산업 일치: {'예' if breakdown.get('sector_match') else '아니오'}, "
        f"기간수익률(모멘텀): {mom}\n"
        f"- 시세 지표: {_metric_text(metric)}\n"
        f"- 최근 뉴스 요약: {_clean_news_summary(news_summary)}\n"
    )


def _generate_reasons(profile, top):
    """top: [(stock, metric, score, breakdown)] → ({stock_id: reason}, source).

    GMS 가 설정돼 있으면 종목별로 호출하고, 실패한 항목만 템플릿으로 메운다.
    """
    client = gms.provider()
    use_gms = client.available()
    out = {}
    any_gms = False
    news_by_stock, news_articles_by_stock = _news_context_for([stock for stock, *_ in top])
    for rank, (stock, metric, score, breakdown) in enumerate(top, start=1):
        reason = None
        if use_gms:
            try:
                reason = client.generate(
                    _build_prompt(
                        profile,
                        stock,
                        metric,
                        rank,
                        score,
                        breakdown,
                        news_by_stock.get(stock.id, ""),
                    )
                )
                any_gms = True
            except gms.GmsError as exc:
                logger.warning(
                    "GMS reason generation failed for stock %s: %s",
                    stock.code,
                    exc,
                )
                reason = None
        if not reason:
            reason = reasons.template_reason(profile, stock, metric, breakdown)
        out[stock.id] = reason
    return out, ("gms" if any_gms else "template"), news_articles_by_stock


@transaction.atomic
def generate_for_user(user):
    """활성 프로필 기준으로 추천을 생성·저장하고 Recommendation 반환. 프로필/후보 없으면 None."""
    profile = active_profile(user)
    if profile is None:
        return None

    stocks = list(Stock.objects.filter(is_active=True).select_related("sector"))
    metrics = {m.stock_id: m for m in StockMetric.objects.filter(stock__in=stocks)}
    candidates = [(s, metrics.get(s.id)) for s in stocks]

    scored = scoring.score_candidates(profile, candidates)
    top = scored[: getattr(settings, "RECOMMENDATION_TOP_N", 5)]
    if not top:
        return None

    # 상위 종목만 실시간 현재가 갱신(표시용; 호출량 최소화 전략)
    stock_services.ensure_fresh_prices([s for s, _, _, _ in top])
    news.ensure_news_summaries([s for s, _, _, _ in top])

    reason_map, source, news_articles_map = _generate_reasons(profile, top)

    # 기존 활성 추천 무효화 후 새 활성본 생성
    Recommendation.objects.filter(user=user, is_active=True).update(is_active=False)
    rec = Recommendation.objects.create(
        user=user, risk_type=profile.risk_type, reason_source=source
    )
    RecommendationItem.objects.bulk_create(
        [
            RecommendationItem(
                recommendation=rec,
                stock=stock,
                rank=i + 1,
                score=score,
                reason=reason_map.get(stock.id, ""),
                breakdown={k: round(v, 3) for k, v in breakdown.items()},
                news_articles=news_articles_map.get(stock.id, []),
            )
            for i, (stock, _metric, score, breakdown) in enumerate(top)
        ]
    )
    return rec
