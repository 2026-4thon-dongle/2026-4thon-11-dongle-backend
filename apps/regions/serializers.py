from rest_framework import serializers

from .models import Region


class RegionSerializer(serializers.ModelSerializer[Region]):
    """다른 도메인 응답에 들어가는 지역 요약."""

    class Meta:
        model = Region
        fields = ["id", "name", "full_name"]
        read_only_fields = fields


class RegionChildSerializer(serializers.ModelSerializer[Region]):
    class Meta:
        model = Region
        fields = ["id", "name", "can_be_hometown", "can_be_residence"]
        read_only_fields = fields


class RegionTreeSerializer(serializers.ModelSerializer[Region]):
    children = RegionChildSerializer(many=True, read_only=True)

    class Meta:
        model = Region
        fields = [
            "id",
            "name",
            "short_name",
            "is_metropolitan",
            "can_be_hometown",
            "can_be_residence",
            "children",
        ]
        read_only_fields = fields
