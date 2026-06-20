from rest_framework import serializers

from .models import RecommendationItem, RecommendationRun


class RecommendationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationItem
        fields = (
            "rank",
            "stock_name",
            "stock_code",
            "sector",
            "current_price",
            "score",
            "reason",
            "news_title",
            "news_url",
        )


class RecommendationRunSerializer(serializers.ModelSerializer):
    items = RecommendationItemSerializer(many=True, read_only=True)

    class Meta:
        model = RecommendationRun
        fields = (
            "id",
            "analysis_summary",
            "profile_snapshot",
            "used_ai",
            "created_at",
            "items",
        )
