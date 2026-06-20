from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CheckUsernameView,
    InvestmentProfileView,
    LoginView,
    LogoutView,
    MeView,
    SignupView,
)

urlpatterns = [
    path("check-username/", CheckUsernameView.as_view()),  # F102
    path("signup/", SignupView.as_view()),  # F103
    path("login/", LoginView.as_view()),  # F105
    path("token/refresh/", TokenRefreshView.as_view()),  # F106
    path("logout/", LogoutView.as_view()),  # F107
    path("me/", MeView.as_view()),  # F108, F109
    path("investment-profile/", InvestmentProfileView.as_view()),  # F200~F210
]
