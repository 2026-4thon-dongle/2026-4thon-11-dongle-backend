"""우체통 응답 형식. 문서(Swagger)와 응답 모양을 한곳에서 정한다."""

from typing import Any

from rest_framework import serializers

from apps.regions.serializers import RegionWithSidoSerializer
from apps.users.models import User

from .mailbox import CLOSED, IN_TRANSIT, MY_TURN, WAITING
from .serializers import StampBriefSerializer

STATUS_CHOICES = [MY_TURN, WAITING, IN_TRANSIT, CLOSED]


def _direction() -> serializers.CharField:
    return serializers.CharField(help_text="sent: 내가 보냄 / received: 내가 받음")


class PartnerSerializer(serializers.ModelSerializer[User]):
    region = RegionWithSidoSerializer(
        source="residence", allow_null=True, help_text="상대 거주 지역"
    )

    class Meta:
        model = User
        fields = ["id", "nickname", "avatar", "region"]
        read_only_fields = fields
        extra_kwargs = {"avatar": {"help_text": "프로필 고향이 표정 code"}}


class SummarySerializer(serializers.Serializer[Any]):
    new_count = serializers.IntegerField(help_text="새 편지 탭의 편지 수")
    new_unread_count = serializers.IntegerField(help_text="그중 안 읽은 편지 수 (빨간 점)")
    my_turn_count = serializers.IntegerField(help_text="내 차례인 대화 수")
    in_transit_count = serializers.IntegerField(help_text="배송 중 탭의 편지 수")


class DiaryBriefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    body_preview = serializers.CharField()


class NewLetterSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    sender = PartnerSerializer()
    from_region = RegionWithSidoSerializer()
    diary = DiaryBriefSerializer(allow_null=True, help_text="답장 대상인 내 일기. 지웠으면 null")
    duration_minutes = serializers.IntegerField()
    arrived_at = serializers.DateTimeField()
    is_read = serializers.BooleanField()
    stamp = StampBriefSerializer()


class LastLetterSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    direction = _direction()
    preview = serializers.CharField(allow_null=True, help_text="도착한 받은 편지만. 그 외 null")
    arrived_at = serializers.DateTimeField(allow_null=True, help_text="도착 전이면 null")
    arrives_at = serializers.DateTimeField()


class ConversationItemSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    partner = PartnerSerializer()
    status = serializers.ChoiceField(STATUS_CHOICES)
    round_trips = serializers.IntegerField(help_text="완성된 왕복 수")
    is_penpal = serializers.BooleanField()
    last_letter = LastLetterSerializer()
    closed_at = serializers.DateTimeField(allow_null=True)


class DiaryInfoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    author = serializers.DictField(help_text="id, nickname")
    body_preview = serializers.CharField()
    created_at = serializers.DateTimeField()


class TimelineLetterSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    direction = _direction()
    preview = serializers.CharField(allow_null=True)
    stamp = StampBriefSerializer()
    sent_at = serializers.DateTimeField()
    arrived_at = serializers.DateTimeField(allow_null=True)


class ConversationDetailSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    partner = PartnerSerializer()
    status = serializers.ChoiceField(STATUS_CHOICES)
    round_trips = serializers.IntegerField()
    is_penpal = serializers.BooleanField()
    letter_count = serializers.IntegerField()
    diary = DiaryInfoSerializer(allow_null=True, help_text="시작 일기. 지웠으면 null")
    letters = TimelineLetterSerializer(many=True)
    reply_to = serializers.IntegerField(allow_null=True, help_text="지금 답장할 편지 id")


class InTransitSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    direction = serializers.CharField(help_text="sent: 내가 보냄 / incoming: 나에게 오는 중")
    partner = PartnerSerializer()
    from_region = RegionWithSidoSerializer()
    to_region = RegionWithSidoSerializer()
    sent_at = serializers.DateTimeField()
    arrives_at = serializers.DateTimeField()
    stamp = StampBriefSerializer()


class ArchiveItemSerializer(serializers.Serializer[Any]):
    kind = serializers.CharField(
        help_text="passed_letter: 넘긴 편지 / closed_conversation: 마무리된 대화"
    )
    letter_id = serializers.IntegerField(allow_null=True)
    conversation_id = serializers.IntegerField()
    partner = PartnerSerializer()
    stamp = StampBriefSerializer()
    archived_at = serializers.DateTimeField()


class LetterDetailSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    conversation_id = serializers.IntegerField()
    is_first = serializers.BooleanField()
    direction = _direction()
    sender_nickname = serializers.CharField(help_text="발송 시점 보낸 사람 닉네임 (From.)")
    recipient_nickname = serializers.CharField(help_text="발송 시점 받는 사람 닉네임 (To.)")
    sender = PartnerSerializer()
    recipient = PartnerSerializer()
    from_region = RegionWithSidoSerializer()
    to_region = RegionWithSidoSerializer()
    body = serializers.CharField()
    stationery = serializers.CharField()
    font = serializers.CharField()
    signature = serializers.CharField(allow_null=True, help_text="서명 이미지 URL")
    stickers = serializers.ListField(
        child=serializers.DictField(),
        help_text="붙인 스티커 `code`, `x`, `y`, `rotation`, `scale`(편지지 너비 대비 비율)",
    )
    stamp = StampBriefSerializer()
    sent_at = serializers.DateTimeField()
    arrived_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField()
    is_read = serializers.BooleanField()
    can_reply = serializers.BooleanField()
    can_pass = serializers.BooleanField()


class PenpalSerializer(serializers.Serializer[Any]):
    partner = PartnerSerializer()
    conversation_id = serializers.IntegerField(help_text="가장 최근 대화 id")
    letter_count = serializers.IntegerField(help_text="주고받은 편지 수")
    last_letter_at = serializers.DateTimeField()
