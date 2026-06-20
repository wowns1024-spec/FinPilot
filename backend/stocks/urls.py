from django.urls import path

from .views import StockDetailView, StockListView, TossStatusView

urlpatterns = [
    path("", StockListView.as_view()),
    path("toss/status/", TossStatusView.as_view()),
    path("<str:symbol>/", StockDetailView.as_view()),
]
