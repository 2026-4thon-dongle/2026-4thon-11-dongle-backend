from django.conf import settings
from django.db import models


class Stamp(models.Model):
    """우표 마스터. 지금은 AUTH-09, DIARY-01에 필요한 것만 있고 STAMP 담당이 확장한다."""

    code = models.SlugField(max_length=30, unique=True)
    number = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=30)
    description = models.CharField(max_length=100, blank=True)

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

    class Meta:
        ordering = ["-granted_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "stamp"], name="uniq_user_stamp"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.stamp}"
