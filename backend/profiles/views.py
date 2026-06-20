from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InvestmentProfile, Sector
from .serializers import InvestmentProfileSerializer, SectorSerializer

_NOT_FOUND = {
    "code": "RESOURCE_NOT_FOUND",
    "message": "투자성향을 먼저 등록해 주세요.",
}


def _active_profile(user):
    return InvestmentProfile.objects.filter(user=user, is_active=True).first()


class ProfileOptionsView(APIView):
    """F201 설문 선택지 제공. enum(위험/기간/목적/자산구간) + 활성 관심 산업 목록."""

    def get(self, request):
        def opts(choices):
            return [{"value": v, "label": label} for v, label in choices]

        return Response(
            {
                "available_asset": opts(InvestmentProfile.AssetBand.choices),
                "risk_type": opts(InvestmentProfile.RiskType.choices),
                "investment_period": opts(InvestmentProfile.InvestmentPeriod.choices),
                "investment_goal": opts(InvestmentProfile.InvestmentGoal.choices),
                "sectors": SectorSerializer(
                    Sector.objects.filter(is_active=True), many=True
                ).data,
            }
        )


class InvestmentProfileView(APIView):
    """F207 저장 / F208 조회 / F209 수정 / F210 삭제(soft).

    사용자당 활성 프로필 1건만 유지한다.
    """

    def get(self, request):
        profile = _active_profile(request.user)
        if profile is None:
            return Response(_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        return Response(InvestmentProfileSerializer(profile).data)

    def post(self, request):
        serializer = InvestmentProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        sectors = data.pop("sectors")
        created = not InvestmentProfile.objects.filter(user=request.user).exists()
        # 부분 저장 실패 시 전체 롤백 (F207 예외 처리)
        with transaction.atomic():
            profile, _ = InvestmentProfile.objects.update_or_create(
                user=request.user,
                defaults={**data, "is_active": True},
            )
            profile.sectors.set(sectors)
        return Response(
            InvestmentProfileSerializer(profile).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def patch(self, request):
        profile = _active_profile(request.user)
        if profile is None:
            return Response(_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        serializer = InvestmentProfileSerializer(
            profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        sectors = data.pop("sectors", None)
        with transaction.atomic():
            for field, value in data.items():
                setattr(profile, field, value)
            profile.save()
            if sectors is not None:
                profile.sectors.set(sectors)
        # TODO(F300): 추천 캐시 무효화
        return Response(InvestmentProfileSerializer(profile).data)

    def delete(self, request):
        profile = _active_profile(request.user)
        if profile is None:
            return Response(
                {"code": "RESOURCE_NOT_FOUND", "message": "등록된 투자성향이 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        # soft delete: 행을 지우지 않고 비활성화 (F210)
        profile.is_active = False
        profile.save(update_fields=["is_active", "updated_at"])
        # TODO(F300): 신규 추천 차단 / 기존 추천 결과 무효화
        return Response(
            {
                "message": "투자성향이 삭제되었습니다. 추천을 받으려면 다시 설문을 진행해 주세요."
            }
        )
