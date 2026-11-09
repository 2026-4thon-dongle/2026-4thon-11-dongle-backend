from django.conf import settings
from django.db import models


class Block(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_made"
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_received"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="uniq_block_pair"),
        ]

    def __str__(self) -> str:
        return f"{self.blocker} -> {self.blocked}"


class Report(models.Model):
    class TargetType(models.TextChoices):
        DIARY = "diary", "일기"
        LETTER = "letter", "편지"
        USER = "user", "사용자"

    class Reason(models.TextChoices):
        SPAM = "spam", "스팸·광고"
        ABUSE = "abuse", "욕설·비방"
        SEXUAL = "sexual", "선정적인 내용"
        PERSONAL_INFO = "personal_info", "개인정보 노출"
        ETC = "etc", "기타"

    class Status(models.TextChoices):
        PENDING = "pending", "검토 대기"
        ACTIONED = "actioned", "조치 완료"
        DISMISSED = "dismissed", "기각"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made"
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="reports_received",
    )
    target_type = models.CharField(max_length=10, choices=TargetType.choices)
    target_id = models.PositiveBigIntegerField()
    reason = models.CharField(max_length=20, choices=Reason.choices)
    detail = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["reporter", "target_type", "target_id"], name="uniq_report_per_target"
            ),
        ]
        indexes = [models.Index(fields=["target_type", "target_id"])]

    def __str__(self) -> str:
        return f"{self.target_type}:{self.target_id} ({self.reason})"
