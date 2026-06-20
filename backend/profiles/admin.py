from django.contrib import admin

from .models import InvestmentProfile, Sector


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "code")


@admin.register(InvestmentProfile)
class InvestmentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "risk_type",
        "available_asset",
        "investment_period",
        "investment_goal",
        "is_active",
        "updated_at",
    )
    list_filter = ("risk_type", "investment_period", "investment_goal", "is_active")
    search_fields = ("user__username", "user__email")
    filter_horizontal = ("sectors",)
    readonly_fields = ("created_at", "updated_at")
