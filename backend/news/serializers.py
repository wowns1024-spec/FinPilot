from rest_framework import serializers

from .models import NewsScrap


class NewsScrapSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsScrap
        fields = (
            "id",
            "title",
            "summary",
            "publisher",
            "published_at",
            "link",
            "originallink",
            "sector",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_link(self, value):
        if not value.startswith(("http://", "https://")):
            raise serializers.ValidationError("뉴스 URL 형식이 올바르지 않습니다.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        scrap, _ = NewsScrap.objects.update_or_create(
            user=user,
            link=validated_data["link"],
            defaults={**validated_data, "user": user},
        )
        return scrap
