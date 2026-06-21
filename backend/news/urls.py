from django.urls import path

from .views import NewsListView, NewsScrapDetailView, NewsScrapView

urlpatterns = [
    path("", NewsListView.as_view()),  # GET 목록/검색/종목별/주요 (F501~F504)
    path("scraps/", NewsScrapView.as_view()),  # GET 목록 / POST 추가 (F505)
    path("scraps/<int:article_id>/", NewsScrapDetailView.as_view()),  # DELETE 삭제 (F505)
]
