from django.contrib import admin

from .models import NewsArticle, NewsScrap


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "stock", "sector", "published_at", "fetched_at")
    list_filter = ("source", "sector")
    search_fields = ("title", "summary", "source", "stock__code", "stock__name")
    raw_id_fields = ("stock", "sector")


@admin.register(NewsScrap)
class NewsScrapAdmin(admin.ModelAdmin):
    list_display = ("user", "article", "created_at")
    search_fields = ("user__username", "article__title")
    raw_id_fields = ("user", "article")
