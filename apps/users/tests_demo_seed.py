from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.diaries.models import Diary
from apps.letters.models import Conversation, Letter
from apps.letters.testing import client_for, make_diary, make_user, region, send
from apps.stamps.models import UserStamp

from .demo_seed import DEMO_DOMAIN, demo_users
from .models import User


def run(*args: str) -> str:
    out = StringIO()
    call_command("seed_demo", *args, stdout=out)
    return out.getvalue()


def demo(key: str) -> User:
    return User.objects.get(email=f"{key}@{DEMO_DOMAIN}")


class SeedDemoTests(TestCase):
    def counts(self) -> tuple[int, int, int, int]:
        users = demo_users()
        return (
            users.count(),
            Diary.objects.filter(author__in=users).count(),
            Letter.objects.filter(sender__in=users).count(),
            UserStamp.objects.filter(user__in=users).count(),
        )

    def test_creates_demo_scenario(self) -> None:
        run()
        self.assertEqual(self.counts()[:3], (5, 10, 7))
        hero = client_for(demo("demo1"))
        new = hero.get(reverse("mailbox-new")).json()
        self.assertEqual(len(new["results"]), 1)
        in_transit = hero.get(reverse("mailbox-in-transit")).json()
        self.assertGreaterEqual(len(in_transit["results"]), 1)
        # 우표 5개 이상이라 「밤하늘」 편지지와 스티커가 열려 있다
        self.assertGreaterEqual(UserStamp.objects.filter(user=demo("demo1")).count(), 5)
        self.assertEqual(hero.get(reverse("feed-hometown")).status_code, 200)

    def test_in_transit_letters_ignore_demo_mode(self) -> None:
        with override_settings(LETTER_DEMO_MODE=True):
            run("--arrive-in", "5")
        now = timezone.now()
        pending = Letter.objects.filter(arrives_at__gt=now)
        self.assertEqual(pending.count(), 3)
        soon = pending.order_by("arrives_at").first()
        assert soon is not None
        self.assertLess((soon.arrives_at - now).total_seconds(), 5 * 60 + 5)

    def test_idempotent(self) -> None:
        run()
        first_ids = sorted(demo_users().values_list("id", flat=True))
        first_counts = self.counts()
        run()
        self.assertEqual(sorted(demo_users().values_list("id", flat=True)), first_ids)
        self.assertEqual(self.counts(), first_counts)

    def test_other_users_untouched(self) -> None:
        alice = make_user("앨리스", region("서울", "성북구"), region("부산"))
        bob = make_user("밥", region("부산", "해운대구"), region("서울"))
        diary = make_diary(alice)
        self.assertEqual(send(client_for(bob), diary_id=diary.id).status_code, 201)
        stamps = UserStamp.objects.filter(user__in=[alice, bob]).count()
        run()
        run("--remove")
        self.assertTrue(Diary.objects.filter(id=diary.id).exists())
        self.assertEqual(Letter.objects.filter(sender=bob).count(), 1)
        self.assertEqual(UserStamp.objects.filter(user__in=[alice, bob]).count(), stamps)
        self.assertEqual(demo_users().count(), 0)

    def test_keeps_conversation_with_other_user(self) -> None:
        run()
        outsider = make_user("손님", region("서울", "종로구"), region("부산"))
        diary = Diary.objects.filter(author=demo("demo1")).first()
        assert diary is not None
        self.assertEqual(send(client_for(outsider), diary_id=diary.id).status_code, 201)
        output = run()
        self.assertIn("1개는 지우지 않고 남겼습니다", output)
        self.assertTrue(Diary.objects.filter(id=diary.id).exists())
        self.assertEqual(Conversation.objects.filter(guest=outsider).count(), 1)
        output = run("--remove")
        self.assertIn(f"demo1@{DEMO_DOMAIN}", output)
        self.assertEqual(
            list(demo_users().values_list("email", flat=True)), [f"demo1@{DEMO_DOMAIN}"]
        )
        self.assertEqual(Letter.objects.filter(sender=outsider).count(), 1)

    def test_nickname_taken_changes_nothing(self) -> None:
        make_user("부산갈매기", region("서울", "성북구"))
        with self.assertRaises(CommandError):
            run()
        self.assertEqual(demo_users().count(), 0)
