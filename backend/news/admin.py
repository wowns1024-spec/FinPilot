from django.contrib import admin

from .models import NewsScrap


@admin.register(NewsScrap)
class NewsScrapAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "sector", "publisher", "created_at")
    search_fields = ("title", "summary", "link", "user__username")
    list_filter = ("sector", "created_at")
