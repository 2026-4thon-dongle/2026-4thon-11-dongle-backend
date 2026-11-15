from typing import Any

from django.core.management.base import BaseCommand

from apps.letters.notifications import notify_arrived_letters


class Command(BaseCommand):
    help = "도착한 편지의 도착·첫 왕복 알림을 만든다 (SET-02). 스케줄러로 1분마다 실행한다."

    def handle(self, *args: Any, **options: Any) -> None:
        count = notify_arrived_letters()
        self.stdout.write(f"도착 알림 {count}건을 만들었습니다.")
