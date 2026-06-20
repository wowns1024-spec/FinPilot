from rest_framework import serializers

from .models import InvestmentProfile, Sector


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ("code", "name")


class InvestmentProfileSerializer(serializers.ModelSerializer):
    """투자성향 조회·저장·수정 응답 (F207~F209).

    sectors 는 쓰기 시 산업 code 목록을 받고, 읽기 시 code+name 을 sectors_detail
    로 돌려준다. enum 필드는 *_display 로 한글 라벨을 함께 제공한다.
    """

    sectors = serializers.ListField(child=serializers.CharField(), write_only=True)
    sectors_detail = SectorSerializer(source="sectors", many=True, read_only=True)

    risk_type_display = serializers.CharField(
        source="get_risk_type_display", read_only=True
    )
    available_asset_display = serializers.CharField(
        source="get_available_asset_display", read_only=True
    )
    investment_period_display = serializers.CharField(
        source="get_investment_period_display", read_only=True
    )
    investment_goal_display = serializers.CharField(
        source="get_investment_goal_display", read_only=True
    )

    class Meta:
        model = InvestmentProfile
        fields = (
            "available_asset",
            "available_asset_display",
            "risk_type",
            "risk_type_display",
            "investment_period",
            "investment_period_display",
            "investment_goal",
            "investment_goal_display",
            "sectors",
            "sectors_detail",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("is_active", "created_at", "updated_at")

    def validate_sectors(self, value):
        # 지원(활성) 산업만 남긴다. 미지원 산업은 저장하지 않는다(F206 예외).
        sectors = list(Sector.objects.filter(is_active=True, code__in=value))
        if not sectors:
            raise serializers.ValidationError("관심 산업을 1개 이상 선택해 주세요.")
        return sectors
