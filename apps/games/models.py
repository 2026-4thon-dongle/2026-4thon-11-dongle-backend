from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.letters.models import Letter


class GameRun(models.Model):
    """직접 배달 게임 한 판 (HOLD-01, Figma 9-1·9-2). letter가 없으면 연습이다."""

    class Status(models.TextChoices):
        PLAYING = "playing", "진행 중"
        FINISHED = "finished", "끝남"
        EXPIRED = "expired", "시간 초과"
        ABANDONED = "abandoned", "새 판 시작으로 무효"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="game_runs"
    )
    letter = models.ForeignKey(
        Letter, null=True, blank=True, on_delete=models.SET_NULL, related_name="game_runs"
    )
    # 시작할 때 편지의 배송 구간. 편지가 지워져도 「먼 길」 우표 조건을 계산할 수 있게 남긴다.
    band = models.CharField(max_length=10, blank=True)
    seed = models.PositiveIntegerField()
    course = models.JSONField(default=list)
    piece_total = models.PositiveSmallIntegerField()
    puddle_total = models.PositiveSmallIntegerField()

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLAYING)
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)

    pieces = models.PositiveSmallIntegerField(null=True, blank=True)
    hits = models.PositiveSmallIntegerField(null=True, blank=True)
    stars = models.PositiveSmallIntegerField(null=True, blank=True)
    reduced_seconds = models.PositiveIntegerField(default=0)
    granted_stamps = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["user", "started_at"]),
            models.Index(fields=["letter", "status"]),
        ]

    def __str__(self) -> str:
        target = f"편지 {self.letter_id}" if self.letter_id else "연습"
        return f"{self.user} {target} ({self.status})"

    @property
    def is_practice(self) -> bool:
        return self.letter_id is None and not self.band
