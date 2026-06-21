from django.conf import settings
from django.db import models


class NewsScrap(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="news_scraps",
    )
    title = models.CharField(max_length=300)
    summary = models.TextField(blank=True)
    publisher = models.CharField(max_length=120, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    link = models.URLField(max_length=600)
    originallink = models.URLField(max_length=600, blank=True)
    sector = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "link"],
                name="unique_news_scrap_per_user_link",
            )
        ]

    def __str__(self):
        return f"{self.user_id} - {self.title}"
