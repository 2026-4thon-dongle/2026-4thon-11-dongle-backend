from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.users.demo_seed import DEMO_DOMAIN, DemoSeedError, remove, seed


class Command(BaseCommand):
    help = (
        f"시연용 계정(@{DEMO_DOMAIN})과 데이터를 지우고 다시 만든다. "
        "시연 계정이 아닌 사용자의 데이터는 바꾸지 않는다."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--arrive-in",
            type=int,
            default=3,
            help="시연 중 도착할 편지가 몇 분 뒤 도착할지 (기본 3)",
        )
        parser.add_argument(
            "--remove", action="store_true", help="시연 데이터와 시연 계정을 지운다"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["arrive_in"] < 1:
            raise CommandError("--arrive-in은 1 이상이어야 합니다.")
        try:
            if options["remove"]:
                result = remove()
                self.stdout.write(f"시연 계정 {result.removed_users}개를 지웠습니다.")
                if result.kept_users:
                    self.stdout.write(
                        "다른 사용자와 대화가 있어 남긴 시연 계정: " + ", ".join(result.kept_users)
                    )
                return
            result = seed(arrive_in=options["arrive_in"])
        except DemoSeedError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            f"시연 계정 {result.users}개, 일기 {result.diaries}개, "
            f"편지 {result.letters}통을 만들었습니다."
        )
        if result.kept_conversations:
            self.stdout.write(
                f"다른 사용자와의 대화 {result.kept_conversations}개는 지우지 않고 남겼습니다."
            )
