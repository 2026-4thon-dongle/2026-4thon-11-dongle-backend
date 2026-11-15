from django.conf import settings
from django.db import models


class Stamp(models.Model):
    """우표 마스터. 업적 12종 + 꾸미기 8종 (STAMP-01~05)."""

    class Kind(models.TextChoices):
        ACHIEVEMENT = "achievement", "업적"
        DECORATION = "decoration", "꾸미기"

    class Grade(models.TextChoices):
        COMMON = "common", "일반"
        RARE = "rare", "희귀"
        LEGENDARY = "legendary", "전설"

    code = models.SlugField(max_length=30, unique=True)
    number = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=30)
    description = models.CharField(max_length=100, blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.ACHIEVEMENT)
    grade = models.CharField(max_length=10, choices=Grade.choices, default=Grade.COMMON)

    class Meta:
        ordering = ["number"]

    def __str__(self) -> str:
        return f"No.{self.number:02d} {self.name}"


class UserStamp(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stamps"
    )
    stamp = models.ForeignKey(Stamp, on_delete=models.PROTECT, related_name="grants")
    granted_at = models.DateTimeField(auto_now_add=True)
    # 「하늘빛님과의 편지로 받음」처럼 획득 계기가 된 상대 (7-7). 없으면 null.
    granted_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["-granted_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "stamp"], name="uniq_user_stamp"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.stamp}"


class RewardSeen(models.Model):
    """수집 보상 해금 모달(5-13)을 확인한 기록. 해금 여부 자체는 우표 수로 계산한다."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seen_rewards"
    )
    code = models.SlugField(max_length=40)
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "code"], name="uniq_reward_seen"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.code}"
