from django.conf import settings
from django.db import models


class FeedSeen(models.Model):
    """고향 ↔ 타지 피드를 마지막으로 확인한 시각. 「새 일기 N편」의 기준이다 (FEED-01)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feed_seen"
    )
    seen_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.user} {self.seen_at:%Y-%m-%d %H:%M}"
