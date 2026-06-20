from django.urls import path

from .views import SectorListView, StockDetailView, StockListView

urlpatterns = [
    path("", StockListView.as_view()),  # F401 목록 / F402 검색
    path("sectors/", SectorListView.as_view()),  # 목록 필터용 섹터 (detail 보다 먼저)
    path("<str:code>/", StockDetailView.as_view()),  # F403~F407 상세
]
