from django.conf import settings
from django.db import models


class InvestmentProfile(models.Model):
    """사용자별 투자성향 설문 응답 (F200)."""

    class RiskType(models.TextChoices):
        STABLE = "stable", "안정형"
        STABILITY_SEEKING = "stability_seeking", "안정추구형"
        BALANCED = "balanced", "균형형"
        ACTIVE = "active", "적극투자형"
        AGGRESSIVE = "aggressive", "공격투자형"

    class InvestmentPeriod(models.TextChoices):
        SHORT = "short", "단타"
        SWING = "swing", "스윙"
        LONG = "long", "중장기"

    class InvestmentGoal(models.TextChoices):
        GROWTH = "growth", "자산 증식"
        STABLE_INCOME = "stable_income", "안정적 수익"
        DIVIDEND = "dividend", "배당 수익"
        SHORT_PROFIT = "short_profit", "단기 차익"
        RETIREMENT = "retirement", "노후 대비"

    class InvestmentStyle(models.TextChoices):
        VALUE = "value", "가치 투자"
        GROWTH = "growth", "성장 투자"
        DIVIDEND = "dividend", "배당 투자"
        MOMENTUM = "momentum", "모멘텀"
        NEWS = "news", "뉴스 기반"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="investment_profile",
    )
    available_asset = models.PositiveIntegerField("투자 가능 자산")
    risk_type = models.CharField("투자 성향", max_length=32, choices=RiskType.choices)
    investment_period = models.CharField(
        "투자 기간", max_length=16, choices=InvestmentPeriod.choices
    )
    investment_goal = models.CharField(
        "투자 목적", max_length=32, choices=InvestmentGoal.choices
    )
    investment_style = models.CharField(
        "투자 스타일",
        max_length=32,
        choices=InvestmentStyle.choices,
        blank=True,
    )
    interest_industries = models.JSONField("관심 산업", default=list)
    created_at = models.DateTimeField("생성일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        db_table = "accounts_investmentprofile"

    def __str__(self):
        return f"{self.user.username} 투자성향"
