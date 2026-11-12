from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        LETTER_ARRIVED = "letter_arrived", "편지 도착"
        LETTER_DEPARTED = "letter_departed", "편지 출발"
        LETTER_LOCATION = "letter_location", "배송 위치"
        ROUND_TRIP = "round_trip", "왕복 완료"
        PROMPT = "prompt", "글감"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    title = models.CharField(max_length=50)
    body = models.CharField(max_length=200, blank=True)
    target_id = models.PositiveBigIntegerField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.user}: {self.title}"


class PushToken(models.Model):
    """기기 토큰 저장소. 실제 발송은 푸시 제공자를 정한 뒤 붙인다 (SET-03)."""

    class Platform(models.TextChoices):
        WEB = "web", "웹"
        IOS = "ios", "iOS"
        ANDROID = "android", "Android"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_tokens"
    )
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user} ({self.platform})"
