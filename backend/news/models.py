from django.conf import settings
from django.db import models


class NewsArticle(models.Model):
    """F500 뉴스 기사 캐시.

    토스/뉴스 API 가 종목 뉴스 목록을 직접 주지 않으므로, Google News RSS 검색 결과를
    URL 자연키로 업서트해 보관한다. 스크랩(F505)이 안정적으로 참조할 수 있도록 표시한
    기사는 모두 DB id 를 갖는다.
    """

    url = models.URLField(max_length=600, unique=True)  # 자연키(업서트 기준)
    title = models.CharField(max_length=500)
    summary = models.TextField(blank=True)
    source = models.CharField(max_length=200, blank=True)       # 언론사명
    source_url = models.URLField(max_length=600, blank=True)    # 언론사 홈
    published_at = models.DateTimeField(null=True, blank=True)
    # 수집 맥락(있으면). 종목별 뉴스(F503)·산업별 재조회·폴백 필터에 쓴다.
    stock = models.ForeignKey(
        "stocks.Stock",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="news_articles",
    )
    sector = models.ForeignKey(
        "profiles.Sector",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="news_articles",
    )
    fetched_at = models.DateTimeField(auto_now=True)       # 마지막 갱신 시각
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 최신 발행순(발행시각 없는 항목은 뒤로). SQLite 는 DESC 에서 NULL 을 뒤로 정렬한다.
        ordering = ("-published_at", "-id")

    def __str__(self):
        return self.title[:40]


class NewsScrap(models.Model):
    """F505 뉴스 스크랩(북마크). 사용자×기사 1건."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="news_scraps",
    )
    article = models.ForeignKey(
        NewsArticle, on_delete=models.CASCADE, related_name="scraps"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "article"], name="uniq_user_article_scrap"
            )
        ]

    def __str__(self):
        return f"{self.user_id} ★ {self.article_id}"
