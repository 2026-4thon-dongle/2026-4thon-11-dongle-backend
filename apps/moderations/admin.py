from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.diaries.models import Diary

from .models import Block, Report


@admin.action(description="기각하고 일기 숨김 해제")
def dismiss_and_unhide(
    modeladmin: "admin.ModelAdmin[Report]", request: HttpRequest, queryset: QuerySet[Report]
) -> None:
    diary_ids = list(
        queryset.filter(target_type=Report.TargetType.DIARY).values_list("target_id", flat=True)
    )
    Report.objects.filter(target_type=Report.TargetType.DIARY, target_id__in=diary_ids).update(
        status=Report.Status.DISMISSED
    )
    queryset.update(status=Report.Status.DISMISSED)
    Diary.objects.filter(id__in=diary_ids).update(is_hidden=False)


@admin.action(description="조치 완료로 표시")
def mark_actioned(
    modeladmin: "admin.ModelAdmin[Report]", request: HttpRequest, queryset: QuerySet[Report]
) -> None:
    queryset.update(status=Report.Status.ACTIONED)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "target_type",
        "target_id",
        "target_user",
        "reason",
        "status",
        "created_at",
    ]
    list_filter = ["status", "target_type", "reason"]
    raw_id_fields = ["reporter", "target_user"]
    actions = [dismiss_and_unhide, mark_actioned]


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ["blocker", "blocked", "created_at"]
    raw_id_fields = ["blocker", "blocked"]
