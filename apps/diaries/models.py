from django.conf import settings
from django.db import models
from django.db.models import Exists, OuterRef, Q

from apps.moderations.models import Block, Report
from apps.regions.models import Region
from apps.users.models import User

BODY_MAX_LENGTH = 500


class DiaryQuerySet(models.QuerySet["Diary"]):
    def visible_to(self, viewer: User) -> "DiaryQuerySet":
        """viewer가 볼 수 있는 일기. 피드와 일기 상세는 이 메서드를 거쳐 조회한다."""
        shares_hometown = Exists(
            User.hometowns.through.objects.filter(
                user_id=OuterRef("author_id"),
                region_id__in=viewer.hometowns.values("id"),
            )
        )
        others = self.filter(
            Q(visibility=Diary.Visibility.ALL)
            | (Q(visibility=Diary.Visibility.SAME_HOMETOWN) & shares_hometown),
            is_hidden=False,
        ).exclude(
            Q(author_id__in=Block.objects.filter(blocker=viewer).values("blocked_id"))
            | Q(author_id__in=Block.objects.filter(blocked=viewer).values("blocker_id"))
            # 일기·편지·사용자 중 무엇을 신고했든 그 작성자의 일기를 모두 숨긴다.
            # 탈퇴로 target_user가 비면 NOT IN이 전부를 걸러 내므로 null은 뺀다.
            | Q(
                author_id__in=Report.objects.filter(
                    reporter=viewer, target_user__isnull=False
                ).values("target_user_id")
            )
        )
        return self.filter(author=viewer) | others


class Diary(models.Model):
    class Visibility(models.TextChoices):
        ALL = "all", "모두에게"
        SAME_HOMETOWN = "same_hometown", "같은 고향 사람에게만"
        PRIVATE = "private", "나만 보기"

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="diaries"
    )
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="diaries")
    body = models.CharField(max_length=BODY_MAX_LENGTH)
    image = models.ImageField(upload_to="diaries/%Y/%m/", null=True, blank=True)
    accepts_letters = models.BooleanField(default=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.ALL)
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DiaryQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["region", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.author} {self.created_at:%Y-%m-%d}"


class DiaryPrompt(models.Model):
    """오늘의 글감 (DIARY-03). 내용은 admin에서 고친다."""

    text = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.text
