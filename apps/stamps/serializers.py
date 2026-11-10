from rest_framework import serializers

from .models import Stamp


class StampSerializer(serializers.ModelSerializer[Stamp]):
    class Meta:
        model = Stamp
        fields = ["code", "number", "name", "description"]
        read_only_fields = fields
        extra_kwargs = {
            "code": {"help_text": "우표 코드. 예: first-step, first-diary"},
            "number": {"help_text": "우표 번호 (도감 순서)"},
            "name": {"help_text": "우표 이름"},
            "description": {"help_text": "우표 설명"},
        }
