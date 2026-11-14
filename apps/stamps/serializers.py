from typing import Any

from rest_framework import serializers

from .models import Stamp


class StampSerializer(serializers.ModelSerializer[Stamp]):
    class Meta:
        model = Stamp
        fields = ["code", "number", "name", "description", "kind", "grade"]
        read_only_fields = fields
        extra_kwargs = {
            "code": {"help_text": "우표 코드. 예: first-step, first-diary"},
            "number": {"help_text": "우표 번호 (도감 순서, No.01 → 1)"},
            "name": {"help_text": "우표 이름"},
            "description": {"help_text": "획득 조건 문구"},
            "kind": {"help_text": "achievement: 업적 우표 / decoration: 꾸미기 우표"},
            "grade": {"help_text": "common: 일반 / rare: 희귀 / legendary: 전설"},
        }


class StampBookItemSerializer(StampSerializer):
    owned = serializers.BooleanField(help_text="보유 여부")
    granted_at = serializers.DateTimeField(allow_null=True, help_text="받은 시각. 없으면 null")

    class Meta(StampSerializer.Meta):
        fields = [*StampSerializer.Meta.fields, "owned", "granted_at"]
        read_only_fields = fields


class RewardBriefSerializer(serializers.Serializer[Any]):
    code = serializers.CharField(help_text="수집 보상 코드")
    name = serializers.CharField(help_text="보상 이름")


class NextRewardSerializer(RewardBriefSerializer):
    threshold = serializers.IntegerField(help_text="필요한 우표 수")
    remaining = serializers.IntegerField(help_text="남은 우표 수")


class StampBookSerializer(serializers.Serializer[Any]):
    owned_count = serializers.IntegerField(help_text="보유 우표 수(업적 + 꾸미기). 수집 보상 기준")
    total_count = serializers.IntegerField(help_text="전체 우표 수")
    next_reward = NextRewardSerializer(
        allow_null=True, help_text="다음 수집 보상. 모두 받았으면 null"
    )
    received_rewards = RewardBriefSerializer(many=True, help_text="받은 보상")
    stamps = StampBookItemSerializer(many=True, help_text="우표 목록 (번호순)")


class UserBriefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nickname = serializers.CharField()


class StampDetailSerializer(StampBookItemSerializer):
    granted_with = UserBriefSerializer(
        allow_null=True, help_text="획득 계기가 된 상대. 없으면 null"
    )
    owned_count = serializers.IntegerField(help_text="보유 우표 수")
    next_reward = NextRewardSerializer(allow_null=True, help_text="다음 수집 보상")

    class Meta(StampBookItemSerializer.Meta):
        fields = [
            *StampBookItemSerializer.Meta.fields,
            "granted_with",
            "owned_count",
            "next_reward",
        ]
        read_only_fields = fields


class RewardItemSerializer(serializers.Serializer[Any]):
    type = serializers.CharField(help_text="sticker / stationery / font / stamp")
    code = serializers.CharField(help_text="아이템 코드")


class RewardSerializer(serializers.Serializer[Any]):
    code = serializers.CharField(help_text="수집 보상 코드")
    threshold = serializers.IntegerField(help_text="필요한 우표 수 (3 / 5 / 10 / 15)")
    name = serializers.CharField(help_text="보상 이름")
    description = serializers.CharField(help_text="보상 설명")
    items = RewardItemSerializer(many=True, help_text="열리는 아이템")
    unlocked = serializers.BooleanField(help_text="열렸는지")
    unlocked_at = serializers.DateTimeField(allow_null=True, help_text="열린 시각")
    seen = serializers.BooleanField(help_text="해금 모달(5-13)을 확인했는지")


class RewardListSerializer(serializers.Serializer[Any]):
    owned_count = serializers.IntegerField(help_text="보유 우표 수")
    rewards = RewardSerializer(many=True, help_text="수집 보상, threshold 오름차순")
