from django.conf import settings
from django.db import models


class RecommendationRun(models.Model):
    """사용자별 AI 종목 추천 실행 이력 (F300)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendation_runs",
    )
    profile_snapshot = models.JSONField(default=dict)
    analysis_summary = models.TextField()
    used_ai = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} 추천 #{self.pk}"


class RecommendationItem(models.Model):
    """추천 종목 단위 결과."""

    run = models.ForeignKey(
        RecommendationRun,
        on_delete=models.CASCADE,
        related_name="items",
    )
    rank = models.PositiveSmallIntegerField()
    stock_name = models.CharField(max_length=80)
    stock_code = models.CharField(max_length=20)
    sector = models.CharField(max_length=40)
    current_price = models.PositiveIntegerField()
    score = models.PositiveSmallIntegerField()
    reason = models.TextField()
    news_title = models.CharField(max_length=160, blank=True)
    news_url = models.URLField(blank=True)

    class Meta:
        ordering = ["rank"]
        unique_together = ("run", "rank")

    def __str__(self):
        return f"{self.rank}. {self.stock_name}"

# Create your models here.
