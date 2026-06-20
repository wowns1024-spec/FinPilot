from django.urls import path

from .views import RecommendationLatestView, RecommendationRequestView

urlpatterns = [
    path("latest/", RecommendationLatestView.as_view()),
    path("request/", RecommendationRequestView.as_view()),
]
