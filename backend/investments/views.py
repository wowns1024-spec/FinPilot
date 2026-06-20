from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InvestmentProfile
from .serializers import InvestmentProfileSerializer


class InvestmentProfileView(APIView):
    """F200 투자성향 저장/조회/수정/삭제."""

    permission_classes = [IsAuthenticated]

    def get_object(self, user):
        try:
            return user.investment_profile
        except InvestmentProfile.DoesNotExist:
            return None

    def get(self, request):
        profile = self.get_object(request.user)
        if profile is None:
            return Response(
                {"detail": "등록된 투자 성향이 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(InvestmentProfileSerializer(profile).data)

    def post(self, request):
        profile = self.get_object(request.user)
        serializer = InvestmentProfileSerializer(
            instance=profile,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK if profile else status.HTTP_201_CREATED,
        )

    def patch(self, request):
        profile = self.get_object(request.user)
        if profile is None:
            return Response(
                {"detail": "등록된 투자 성향이 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = InvestmentProfileSerializer(
            instance=profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request):
        profile = self.get_object(request.user)
        if profile is not None:
            profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
