from django.contrib import admin

from .models import Recommendation, RecommendationItem, StockMetric, StockNewsSummary


@admin.register(StockMetric)
class StockMetricAdmin(admin.ModelAdmin):
    list_display = ("stock", "volatility", "momentum", "liquidity", "as_of")
    search_fields = ("stock__code", "stock__name")


@admin.register(StockNewsSummary)
class StockNewsSummaryAdmin(admin.ModelAdmin):
    list_display = ("stock", "source", "as_of", "updated_at")
    search_fields = ("stock__code", "stock__name", "summary")


class RecommendationItemInline(admin.TabularInline):
    model = RecommendationItem
    extra = 0


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active", "reason_source", "created_at")
    list_filter = ("is_active", "reason_source")
    inlines = [RecommendationItemInline]
