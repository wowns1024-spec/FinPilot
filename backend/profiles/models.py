from django.conf import settings
from django.db import models


class Sector(models.Model):
    """관심 산업 마스터 (F206). 추천 후보군·뉴스 키워드 구성에 쓰인다.

    is_active=False 인 산업은 설문 선택지에 노출되지 않으며 저장 대상에서 제외된다.
    """

    code = models.CharField(max_length=30, unique=True)  # 예: "SEMICONDUCTOR"
    name = models.CharField(max_length=50)  # 예: "반도체"
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("order", "id")

    def __str__(self):
        return self.name


class InvestmentProfile(models.Model):
    """F200 투자성향. 사용자당 1건(User 와 OneToOne), 재저장 시 upsert.

    명세 §5.2 의 선호 입력 방식(점수 퀴즈가 아니라 직접 선택)을 따른다.
    related_name 은 accounts.User.has_investment_profile 가 참조하는
    ``investment_profile`` 과 일치해야 한다. 삭제(F210)는 행 제거가 아니라
    is_active=False 로의 비활성화(soft delete)로 처리한다.
    """

    class RiskType(models.TextChoices):  # F203 위험 선호도
        STABLE = "STABLE", "안정형"
        STABLE_SEEKING = "STABLE_SEEKING", "안정추구형"
        BALANCED = "BALANCED", "균형형"
        ACTIVE = "ACTIVE", "적극투자형"
        AGGRESSIVE = "AGGRESSIVE", "공격투자형"

    class AssetBand(models.IntegerChoices):  # F202 투자 가능 자산(금액 구간 코드)
        UNDER_10M = 1, "1천만 원 미만"
        M10_TO_50 = 2, "1천만~5천만 원"
        M50_TO_100 = 3, "5천만~1억 원"
        M100_TO_500 = 4, "1억~5억 원"
        OVER_500M = 5, "5억 원 이상"

    class InvestmentPeriod(models.TextChoices):  # F204 투자 기간
        SHORT = "SHORT", "단타"
        SWING = "SWING", "스윙"
        LONG = "LONG", "중장기"

    class InvestmentGoal(models.TextChoices):  # F205 투자 목적
        GROWTH = "GROWTH", "자산증식"
        STABLE_INCOME = "STABLE_INCOME", "안정적수익"
        DIVIDEND = "DIVIDEND", "배당수익"
        SHORT_TERM_GAIN = "SHORT_TERM_GAIN", "단기차익"
        RETIREMENT = "RETIREMENT", "노후대비"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="investment_profile",
    )
    available_asset = models.PositiveSmallIntegerField(choices=AssetBand.choices)
    risk_type = models.CharField(max_length=20, choices=RiskType.choices)
    investment_period = models.CharField(max_length=10, choices=InvestmentPeriod.choices)
    investment_goal = models.CharField(max_length=20, choices=InvestmentGoal.choices)
    sectors = models.ManyToManyField(Sector, related_name="profiles")  # 최소 1개
    is_active = models.BooleanField(default=True)  # F210 soft delete
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        state = "" if self.is_active else " (비활성)"
        return f"{self.user.username} · {self.get_risk_type_display()}{state}"
