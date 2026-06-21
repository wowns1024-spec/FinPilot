from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from stocks import services as stock_services

from . import services
from .models import Recommendation
from .serializers import RecommendationSerializer


def _refresh_and_serialize(rec):
    """추천 종목(상위 N개)의 현재가만 갱신 후 직렬화."""
    items = list(rec.items.select_related("stock"))
    stock_services.ensure_fresh_prices([it.stock for it in items])
    return RecommendationSerializer(rec).data


class RecommendationView(APIView):
    """F300 맞춤 추천 — 생성(POST)·조회(GET). 인증 필요(사용자별)."""

    def get(self, request):
        rec = Recommendation.objects.filter(user=request.user, is_active=True).first()
        if rec is None:
            return Response(
                {"code": "RESOURCE_NOT_FOUND", "message": "추천을 먼저 생성해 주세요."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(_refresh_and_serialize(rec))

    def post(self, request):
        if services.active_profile(request.user) is None:
            return Response(
                {"code": "PROFILE_REQUIRED", "message": "투자성향을 먼저 등록해 주세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rec = services.generate_for_user(request.user)
        if rec is None:
            return Response(
                {
                    "code": "NO_CANDIDATES",
                    "message": "추천할 종목이 없습니다. 잠시 후 다시 시도해 주세요.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(_refresh_and_serialize(rec), status=status.HTTP_201_CREATED)
