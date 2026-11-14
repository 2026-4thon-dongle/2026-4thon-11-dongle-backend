from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.diaries.models import Diary
from apps.regions.models import Region
from apps.stamps.models import Stamp

BODY_MAX_LENGTH = 1000
# 마지막 편지가 도착한 뒤 이만큼 답장이 없으면 대화가 마무리된다 (5-3, 가정)
CLOSE_AFTER = timedelta(days=7)


class Conversation(models.Model):
    """일기 하나와 두 사람의 편지 묶음. 첫 편지가 만든다."""

    diary = models.ForeignKey(
        Diary, null=True, blank=True, on_delete=models.SET_NULL, related_name="conversations"
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_conversations"
    )
    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="guest_conversations"
    )
    # 일기 작성자(host)가 첫 편지를 넘긴 시각 (MAIL-06)
    passed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            # 같은 일기에 같은 사람이 첫 편지는 한 통만 (가정)
            models.UniqueConstraint(fields=["diary", "guest"], name="uniq_first_letter_per_diary"),
        ]

    def __str__(self) -> str:
        return f"{self.guest} → {self.host} ({self.diary_id})"

    def partner_of(self, user_id: int) -> int:
        return self.guest_id if user_id == self.host_id else self.host_id


class Letter(models.Model):
    class Band(models.TextChoices):
        SAME_SIDO = "same_sido", "같은 시·도"
        ADJACENT = "adjacent", "인접 시·도"
        NEAR = "near", "300km 미만"
        FAR = "far", "300km 이상·바다 건너"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="letters")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_letters"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_letters"
    )
    # 닉네임을 바꿔도 보낸 편지는 그대로다 (7-9)
    sender_nickname = models.CharField(max_length=10)
    recipient_nickname = models.CharField(max_length=10)
    reply_to = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reply"
    )
    is_first = models.BooleanField(default=False)

    from_region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="+")
    to_region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="+")
    band = models.CharField(max_length=10, choices=Band.choices)
    duration_minutes = models.PositiveIntegerField()

    body = models.CharField(max_length=BODY_MAX_LENGTH)
    stationery = models.CharField(max_length=30)
    font = models.CharField(max_length=30)
    signature = models.ImageField(upload_to="signatures/%Y/%m/", null=True, blank=True)
    stickers = models.JSONField(default=list, blank=True)
    stamp = models.ForeignKey(Stamp, on_delete=models.PROTECT, related_name="+")

    sent_at = models.DateTimeField(default=timezone.now)
    arrives_at = models.DateTimeField()
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["sent_at", "id"]
        indexes = [
            models.Index(fields=["recipient", "arrives_at"]),
            models.Index(fields=["sender", "sent_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.sender_nickname} → {self.recipient_nickname} ({self.sent_at:%Y-%m-%d})"

    def has_arrived(self, now: datetime | None = None) -> bool:
        return self.arrives_at <= (now or timezone.now())
