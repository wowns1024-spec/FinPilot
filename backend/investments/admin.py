from django.contrib import admin

from .models import InvestmentProfile


@admin.register(InvestmentProfile)
class InvestmentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "available_asset",
        "risk_type",
        "investment_period",
        "investment_goal",
        "updated_at",
    )
    search_fields = ("user__username", "user__email")
    list_filter = ("risk_type", "investment_period", "investment_goal")
