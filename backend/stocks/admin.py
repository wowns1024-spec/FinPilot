from django.contrib import admin

from .models import Quote, Stock


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "market", "sector", "is_active")
    list_filter = ("market", "sector", "is_active")
    search_fields = ("code", "name")
    list_select_related = ("sector",)


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("stock", "last_price", "prev_close", "volume", "updated_at")
    search_fields = ("stock__code", "stock__name")
