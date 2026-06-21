from rest_framework import serializers

from profiles.models import InvestmentProfile
from stocks import services as stock_services
from stocks.models import Quote

from .models import Recommendation, RecommendationItem


class RecommendationItemSerializer(serializers.ModelSerializer):
    """추천 종목 1건: 순위·점수·이유 + 현재 시세(stocks 직렬화 재사용)."""

    stock = serializers.SerializerMethodField()

    class Meta:
        model = RecommendationItem
        fields = ("rank", "score", "reason", "breakdown", "news_articles", "stock")

    def get_stock(self, obj):
        quote = self.context["quotes"].get(obj.stock_id)
        return stock_services.serialize_list_item(obj.stock, quote)


class RecommendationSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    risk_type_display = serializers.SerializerMethodField()

    class Meta:
        model = Recommendation
        fields = (
            "id",
            "is_active",
            "reason_source",
            "risk_type",
            "risk_type_display",
            "created_at",
            "items",
        )

    def get_items(self, obj):
        items = list(obj.items.select_related("stock", "stock__sector"))
        quotes = {
            q.stock_id: q
            for q in Quote.objects.filter(stock__in=[it.stock_id for it in items])
        }
        return RecommendationItemSerializer(
            items, many=True, context={"quotes": quotes}
        ).data

    def get_risk_type_display(self, obj):
        return dict(InvestmentProfile.RiskType.choices).get(obj.risk_type, obj.risk_type)
