from django.urls import path

from .views import InvestmentProfileView, ProfileOptionsView

urlpatterns = [
    path("", InvestmentProfileView.as_view()),  # F207 저장 / F208 조회 / F209 수정 / F210 삭제
    path("options/", ProfileOptionsView.as_view()),  # F201 설문 선택지
]
