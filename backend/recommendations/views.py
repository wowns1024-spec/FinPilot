from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RecommendationItem, RecommendationRun
from .serializers import RecommendationRunSerializer
from .services import generate_recommendations


class RecommendationLatestView(APIView):
    """F307 최근 추천 결과 조회."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        run = request.user.recommendation_runs.first()
        if run is None:
            return Response(
                {"detail": "아직 생성된 추천 결과가 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(RecommendationRunSerializer(run).data)


class RecommendationRequestView(APIView):
    """F301 AI 종목 추천 요청."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = getattr(request.user, "investment_profile", None)
        if profile is None:
            return Response(
                {
                    "code": "INVESTMENT_PROFILE_REQUIRED",
                    "message": "투자 성향 설문을 먼저 작성해 주세요.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        result = generate_recommendations(profile)
        run = RecommendationRun.objects.create(
            user=request.user,
            profile_snapshot=result["profile_snapshot"],
            analysis_summary=result["analysis_summary"],
            used_ai=result["used_ai"],
        )
        RecommendationItem.objects.bulk_create(
            RecommendationItem(run=run, **item) for item in result["items"]
        )
        return Response(
            RecommendationRunSerializer(run).data,
            status=status.HTTP_201_CREATED,
        )

# Create your views here.
