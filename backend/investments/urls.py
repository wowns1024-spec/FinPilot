from django.urls import path

from .views import InvestmentProfileView

urlpatterns = [
    path("profile/", InvestmentProfileView.as_view()),
]
