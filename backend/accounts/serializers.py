from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import InvestmentProfile

User = get_user_model()

INTEREST_INDUSTRY_CHOICES = {
    "semiconductor": "반도체",
    "battery": "2차전지",
    "defense": "방산",
    "ai": "AI",
    "energy": "에너지",
    "game": "게임",
    "bio": "바이오",
    "consumer": "소비재",
    "finance": "금융",
    "auto": "자동차",
}


class UserSummarySerializer(serializers.ModelSerializer):
    """회원정보 조회 응답 (F108)."""

    has_investment_profile = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "birth_date",
            "date_joined",
            "has_investment_profile",
        )
        read_only_fields = fields


class SignupSerializer(serializers.ModelSerializer):
    """회원가입 처리 (F103). 입력 검증은 F104 기준."""

    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    email = serializers.EmailField(required=True)
    birth_date = serializers.DateField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "birth_date", "password", "password_confirm")

    def validate_username(self, value):
        value = value.strip()
        # F102 대소문자 무관 중복 정책
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("이미 사용 중인 아이디입니다.")
        return value

    def validate_email(self, value):
        # 이메일 중복 불가 (대소문자 무관)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "비밀번호가 일치하지 않습니다."}
            )
        # Django 비밀번호 정책 검증
        temp_user = User(username=attrs.get("username"), email=attrs.get("email"))
        validate_password(attrs["password"], user=temp_user)
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)  # 해시 저장 (NF102)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """회원정보 수정 (F109). 이메일/비밀번호 변경."""

    current_password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        write_only=True, required=False, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ("email", "current_password", "new_password")

    def validate_email(self, value):
        # 본인을 제외한 이메일 중복 불가
        if (
            User.objects.filter(email__iexact=value)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise serializers.ValidationError("이미 사용 중인 이메일입니다.")
        return value

    def validate(self, attrs):
        user = self.instance
        new_password = attrs.get("new_password")
        if new_password:
            current = attrs.get("current_password")
            if not current or not user.check_password(current):
                raise serializers.ValidationError(
                    {"current_password": "현재 비밀번호가 올바르지 않습니다."}
                )
            validate_password(new_password, user=user)
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("current_password", None)
        new_password = validated_data.pop("new_password", None)
        if "email" in validated_data:
            instance.email = validated_data["email"]
        if new_password:
            instance.set_password(new_password)
        instance.save()
        return instance


class InvestmentProfileSerializer(serializers.ModelSerializer):
    """투자성향 입력/조회/수정 (F200~F210)."""

    risk_type_label = serializers.CharField(source="get_risk_type_display", read_only=True)
    investment_period_label = serializers.CharField(
        source="get_investment_period_display", read_only=True
    )
    investment_goal_label = serializers.CharField(
        source="get_investment_goal_display", read_only=True
    )
    investment_style_label = serializers.CharField(
        source="get_investment_style_display", read_only=True
    )
    interest_industry_labels = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentProfile
        fields = (
            "id",
            "available_asset",
            "risk_type",
            "risk_type_label",
            "investment_period",
            "investment_period_label",
            "investment_goal",
            "investment_goal_label",
            "investment_style",
            "investment_style_label",
            "interest_industries",
            "interest_industry_labels",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "risk_type_label",
            "investment_period_label",
            "investment_goal_label",
            "investment_style_label",
            "interest_industry_labels",
            "created_at",
            "updated_at",
        )

    def get_interest_industry_labels(self, obj):
        return [
            INTEREST_INDUSTRY_CHOICES[value]
            for value in obj.interest_industries
            if value in INTEREST_INDUSTRY_CHOICES
        ]

    def validate_available_asset(self, value):
        if value <= 0:
            raise serializers.ValidationError("투자 가능 자산은 1원 이상이어야 합니다.")
        return value

    def validate_interest_industries(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("관심 산업은 목록 형식이어야 합니다.")
        cleaned = []
        for item in value:
            if item not in INTEREST_INDUSTRY_CHOICES:
                raise serializers.ValidationError("선택할 수 없는 관심 산업입니다.")
            if item not in cleaned:
                cleaned.append(item)
        if not cleaned:
            raise serializers.ValidationError("관심 산업을 1개 이상 선택해 주세요.")
        return cleaned


class LoginSerializer(TokenObtainPairSerializer):
    """로그인 처리 (F105). 토큰과 함께 사용자 요약정보 반환."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSummarySerializer(self.user).data
        return data
