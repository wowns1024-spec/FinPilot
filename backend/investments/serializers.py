from rest_framework import serializers

from .choices import INTEREST_INDUSTRY_CHOICES
from .models import InvestmentProfile


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
