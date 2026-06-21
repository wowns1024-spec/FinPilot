from django.urls import path

from .views import (
    NewsCategoryView,
    NewsDetailView,
    NewsListView,
    NewsScrapDeleteView,
    NewsScrapListCreateView,
)

urlpatterns = [
    path("", NewsListView.as_view()),
    path("detail/", NewsDetailView.as_view()),
    path("categories/", NewsCategoryView.as_view()),
    path("scraps/", NewsScrapListCreateView.as_view()),
    path("scraps/<int:pk>/", NewsScrapDeleteView.as_view()),
]
