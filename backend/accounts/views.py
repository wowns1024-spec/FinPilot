from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import InvestmentProfile
from .serializers import (
    InvestmentProfileSerializer,
    LoginSerializer,
    SignupSerializer,
    UserSummarySerializer,
    UserUpdateSerializer,
)

User = get_user_model()


def _tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class CheckUsernameView(APIView):
    """F102 아이디 중복 확인."""

    permission_classes = [AllowAny]

    def get(self, request):
        username = (request.query_params.get("username") or "").strip()
        if not username:
            return Response(
                {"code": "VALIDATION_ERROR", "message": "아이디를 입력해 주세요."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        available = not User.objects.filter(username__iexact=username).exists()
        return Response(
            {
                "username": username,
                "available": available,
                "message": "사용 가능한 아이디입니다."
                if available
                else "이미 사용 중인 아이디입니다.",
            }
        )


class SignupView(APIView):
    """F103 회원가입 처리. 성공 시 JWT 발급 + 사용자 요약 반환."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                **_tokens_for(user),
                "user": UserSummarySerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """F105 로그인 처리."""

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer


class LogoutView(APIView):
    """F107 로그아웃 처리. Refresh Token 블랙리스트 등록."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                # 이미 만료/무효한 토큰이어도 로그아웃은 성공으로 처리
                pass
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    """F108 회원정보 조회 / F109 회원정보 수정."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSummarySerializer(request.user).data)

    def patch(self, request):
        serializer = UserUpdateSerializer(
            instance=request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSummarySerializer(request.user).data)


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
