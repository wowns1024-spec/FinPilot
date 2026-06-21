from django.urls import path

from .views import RecommendationView

urlpatterns = [
    path("", RecommendationView.as_view()),  # GET 조회 / POST 생성 (F300)
]
