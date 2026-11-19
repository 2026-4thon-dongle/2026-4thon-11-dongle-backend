from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.diaries.models import Diary
from apps.feeds.models import FeedSeen
from apps.games.models import GameRun
from apps.letters.models import Conversation, Draft, Letter
from apps.notifications.models import Notification


class Command(BaseCommand):
    help = (
        "일기·편지·대화·임시저장·배달 게임 기록·알림을 모두 지운다. "
        "계정, 우표, 차단·신고는 그대로 둔다. 되돌릴 수 없으니 먼저 백업한다."
    )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        for model in (GameRun, Draft, Letter, Conversation, Notification, FeedSeen, Diary):
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f"{model.__name__}: {count}개 삭제")
