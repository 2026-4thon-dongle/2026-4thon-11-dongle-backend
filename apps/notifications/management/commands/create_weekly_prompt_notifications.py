from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.diaries.models import DiaryPrompt
from apps.notifications.models import Notification
from apps.users.models import User


class Command(BaseCommand):
    help = "이번 주 글감 알림을 만든다 (SET-05). 매주 월요일 스케줄러로 실행한다."

    def handle(self, *args: Any, **options: Any) -> None:
        today = timezone.localdate()
        prompts = list(DiaryPrompt.objects.filter(is_active=True))
        if not prompts:
            self.stdout.write("활성 글감이 없어 건너뜁니다.")
            return
        prompt = prompts[today.isocalendar().week % len(prompts)]

        # 같은 주에 다시 실행해도 중복으로 만들지 않는다.
        already_sent = Notification.objects.filter(
            user=OuterRef("pk"),
            type=Notification.Type.PROMPT,
            created_at__gte=timezone.now() - timedelta(days=6),
        )
        users = User.objects.filter(weekly_prompt_enabled=True, is_active=True).exclude(
            Exists(already_sent)
        )
        created = Notification.objects.bulk_create(
            Notification(
                user=user,
                type=Notification.Type.PROMPT,
                title="이번 주 글감이 도착했어요",
                body=prompt.text,
            )
            for user in users
        )
        self.stdout.write(f"글감 알림 {len(created)}건을 만들었습니다.")
