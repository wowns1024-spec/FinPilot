from rest_framework import serializers

from .models import NewsArticle


class NewsArticleSerializer(serializers.ModelSerializer):
    """뉴스 기사 1건. ``context['scrapped_ids']`` 로 스크랩 여부를 표시한다."""

    is_scrapped = serializers.SerializerMethodField()
    stock_code = serializers.CharField(source="stock.code", default=None, read_only=True)
    stock_name = serializers.CharField(source="stock.name", default=None, read_only=True)

    class Meta:
        model = NewsArticle
        fields = (
            "id",
            "title",
            "summary",
            "source",
            "source_url",
            "url",
            "published_at",
            "stock_code",
            "stock_name",
            "is_scrapped",
        )

    def get_is_scrapped(self, obj):
        return obj.id in self.context.get("scrapped_ids", set())
