from rest_framework import serializers

from .models import Region


class RegionSerializer(serializers.ModelSerializer[Region]):
    """다른 도메인 응답에 들어가는 지역 요약."""

    class Meta:
        model = Region
        fields = ["id", "name", "full_name"]
        read_only_fields = fields
        extra_kwargs = {
            "name": {"help_text": "지역 이름. 예: 강남구"},
            "full_name": {"help_text": "시·도 약칭을 붙인 이름. 예: 서울 강남구"},
        }


class RegionChildSerializer(serializers.ModelSerializer[Region]):
    class Meta:
        model = Region
        fields = ["id", "name", "can_be_hometown", "can_be_residence"]
        read_only_fields = fields
        extra_kwargs = {
            "name": {"help_text": "시·군·구 이름"},
            "can_be_hometown": {"help_text": "본가로 고를 수 있는지"},
            "can_be_residence": {"help_text": "거주 지역으로 고를 수 있는지"},
        }


class RegionTreeSerializer(serializers.ModelSerializer[Region]):
    children = RegionChildSerializer(many=True, read_only=True, help_text="하위 시·군·구 목록")

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
        extra_kwargs = {
            "name": {"help_text": "시·도 이름. 예: 서울특별시"},
            "short_name": {"help_text": "시·도 약칭. 예: 서울"},
            "is_metropolitan": {
                "help_text": "광역시·특별시 여부. true면 시·도 자체를 본가로 고른다."
            },
            "can_be_hometown": {"help_text": "시·도 자체를 본가로 고를 수 있는지"},
            "can_be_residence": {
                "help_text": "시·도 자체를 거주 지역으로 고를 수 있는지 (세종 등)"
            },
        }
