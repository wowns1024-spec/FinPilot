from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import get_stock_detail, list_stocks, toss_config_status, toss_configured


class StockListView(APIView):
    """F401/F402 종목 목록 조회 및 검색."""

    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "")
        try:
            limit = min(int(request.query_params.get("limit", 30)), 100)
        except ValueError:
            limit = 30
        items = list_stocks(query=query, limit=limit)
        return Response(
            {
                "items": items,
                "count": len(items),
                "query": query,
                "toss_configured": toss_configured(),
                "toss_status": toss_config_status(),
            }
        )


class StockDetailView(APIView):
    """F403~F407 종목 상세 조회."""

    permission_classes = [AllowAny]

    def get(self, request, symbol):
        detail = get_stock_detail(symbol)
        if detail is None:
            return Response(
                {"detail": "종목을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(detail)


class TossStatusView(APIView):
    """토스증권 API 설정 상태 조회."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(toss_config_status())
