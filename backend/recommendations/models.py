from django.conf import settings
from django.db import models


class StockMetric(models.Model):
    """F300 점수 산정용 시세 파생 지표 스냅샷.

    토스가 펀더멘털(PER·배당 등)을 주지 않으므로, 일봉 history 에서 계산한
    변동성·모멘텀·유동성을 배치(`compute_metrics`)로 저장해 추천 점수의 입력으로 쓴다.
    실시간이 아닌 '스냅샷' 기준 점수라, 추천마다 외부를 다시 부르지 않는다.
    """

    stock = models.OneToOneField(
        "stocks.Stock", on_delete=models.CASCADE, related_name="metric"
    )
    volatility = models.FloatField(null=True, blank=True)  # 일간수익률 표준편차(클수록 변동↑)
    momentum = models.FloatField(null=True, blank=True)    # 기간수익률((최근-기준)/기준)
    liquidity = models.FloatField(null=True, blank=True)   # 평균 일거래대금(종가×거래량)
    window = models.PositiveSmallIntegerField(default=0)   # 계산에 쓴 캔들 수
    as_of = models.DateField(null=True, blank=True)        # 스냅샷 일자
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.stock.code} metric @ {self.as_of}"


class StockNewsSummary(models.Model):
    """F300 추천 이유 생성에 사용할 종목별 최신 뉴스 요약 스냅샷.

    F500 뉴스 수집/요약 기능이 완성되면 이 테이블을 갱신하고, F300은 생성 시점의
    최신 요약을 GMS 프롬프트에 함께 전달한다.
    """

    stock = models.OneToOneField(
        "stocks.Stock", on_delete=models.CASCADE, related_name="news_summary"
    )
    summary = models.TextField(blank=True)
    articles = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=100, blank=True)
    as_of = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.stock.code} news summary"


class Recommendation(models.Model):
    """F300 추천 결과 묶음. 사용자당 활성(is_active) 1건.

    투자성향이 바뀌면 무효화(is_active=False)되고, 재생성 시 새 활성본이 만들어진다.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )
    is_active = models.BooleanField(default=True)
    risk_type = models.CharField(max_length=20, blank=True)        # 생성 시점 성향 스냅샷
    reason_source = models.CharField(max_length=10, default="template")  # template | gms
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.username} 추천 ({self.created_at:%Y-%m-%d %H:%M})"


class RecommendationItem(models.Model):
    """추천 묶음 내 개별 종목(순위·점수·이유)."""

    recommendation = models.ForeignKey(
        Recommendation, on_delete=models.CASCADE, related_name="items"
    )
    stock = models.ForeignKey("stocks.Stock", on_delete=models.CASCADE)
    rank = models.PositiveSmallIntegerField()
    score = models.FloatField()                       # 0~100
    reason = models.TextField(blank=True)
    breakdown = models.JSONField(default=dict, blank=True)  # 점수 구성요소(설명용)
    news_articles = models.JSONField(default=list, blank=True)  # 추천 이유 생성에 사용한 뉴스 링크 스냅샷

    class Meta:
        ordering = ("rank",)

    def __str__(self):
        return f"#{self.rank} {self.stock.code} ({self.score:.0f})"
