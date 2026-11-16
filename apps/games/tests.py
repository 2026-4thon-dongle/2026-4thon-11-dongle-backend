from datetime import timedelta
from typing import Any

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.letters.models import Letter
from apps.letters.testing import client_for, make_diary, make_user, region, send
from apps.moderations.models import Block
from apps.stamps.models import UserStamp

from . import rules
from .course import PIECE, PUDDLE, build_course, count_kind
from .models import GameRun
from .services import progress


def owned_codes(user: Any) -> set[str]:
    return set(UserStamp.objects.filter(user=user).values_list("stamp__code", flat=True))


class CourseTests(TestCase):
    def test_same_seed_same_course(self) -> None:
        self.assertEqual(build_course(42), build_course(42))
        self.assertNotEqual(build_course(42), build_course(43))

    def test_always_beatable(self) -> None:
        for seed in range(1, 200):
            course = build_course(seed)
            self.assertGreaterEqual(count_kind(course, PIECE), 12, seed)
            rows: dict[float, list[str]] = {}
            for item in course:
                self.assertIn(item["lane"], range(rules.LANES))
                self.assertTrue(0 < item["t"] < rules.RUN_SECONDS, seed)
                rows.setdefault(item["t"], []).append(item["kind"])
            for kinds in rows.values():
                # 한 줄에 조각·물웅덩이는 각각 하나 이하 → 모두 줍고 모두 피할 수 있다
                self.assertLessEqual(kinds.count(PIECE), 1, seed)
                self.assertLessEqual(kinds.count(PUDDLE), 1, seed)

    def test_stars(self) -> None:
        cases = [
            (20, 20, 0, 3),
            (17, 20, 1, 3),
            (17, 20, 2, 2),
            (13, 20, 2, 2),
            (13, 20, 5, 1),
            (8, 20, 9, 1),
            (7, 20, 0, 0),
            (0, 0, 0, 0),
        ]
        for pieces, total, hits, stars in cases:
            self.assertEqual(rules.stars_for(pieces, total, hits), stars, (pieces, total, hits))


@override_settings(LETTER_DEMO_MODE=False)
class GameApiTests(TestCase):
    def setUp(self) -> None:
        # 서울 → 충남: 300km 미만 구간, 6시간
        self.host = make_user("하늘빛", region("충남", "천안시"), hometown=region("서울"))
        self.guest = make_user("다인", region("서울", "성북구"))
        self.guest.hometowns.set(
            [region("충남", "천안시"), region("서울", "종로구"), region("제주", "제주시")]
        )
        self.host_api, self.guest_api = client_for(self.host), client_for(self.guest)
        response = send(self.guest_api, diary_id=make_diary(self.host).id)
        self.assertEqual(response.status_code, 201, response.data)
        self.letter = Letter.objects.get(id=response.data["id"])
        # 새벽에 돌리면 「새벽 편지」 우표가 같이 나가 우표 수가 달라지므로 지운다.
        UserStamp.objects.filter(user=self.guest, stamp__code="dawn-letter").delete()

    def start(self, api: APIClient, letter_id: int | None = None) -> Any:
        data = {} if letter_id is None else {"letter_id": letter_id}
        return api.post(reverse("game-run-start"), data, format="json")

    def finish(self, api: APIClient, run_id: int, pieces: int, hits: int, age: int = 30) -> Any:
        GameRun.objects.filter(id=run_id).update(started_at=timezone.now() - timedelta(seconds=age))
        return api.post(
            reverse("game-run-finish", args=[run_id]), {"pieces": pieces, "hits": hits}, "json"
        )

    def play(self, api: APIClient, stars: int, letter_id: int | None = None) -> Any:
        run = self.start(api, letter_id).data
        total = run["piece_total"]
        pieces = {3: total, 2: int(total * 0.7) + 1, 1: int(total * 0.45) + 1, 0: 0}[stars]
        hits = {3: 1, 2: 2, 1: 3, 0: 0}[stars]
        response = self.finish(api, run["id"], pieces, min(hits, run["puddle_total"]))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["stars"], stars)
        return response.data

    def test_home(self) -> None:
        data = self.guest_api.get(reverse("game-home")).data
        self.assertEqual(data["rules"]["run_seconds"], 30)
        self.assertEqual([s["reduce_seconds"] for s in data["rules"]["stars"]], [1800, 1200, 600])
        self.assertEqual(data["today"], {"played": 0, "limit": 10, "remaining": 10})
        self.assertEqual(len(data["goals"]), 8)
        self.assertTrue(all(g["stamp"]["kind"] == "decoration" for g in data["goals"]))
        letter = data["letters"][0]
        self.assertEqual((letter["id"], letter["direction"]), (self.letter.id, "sent"))
        self.assertEqual(letter["partner"]["nickname"], "하늘빛")
        game = letter["game"]
        self.assertTrue(game["playable"])
        self.assertEqual(game["max_reduce_seconds"], 3 * 60 * 60)
        incoming = self.host_api.get(reverse("game-home")).data["letters"][0]
        self.assertEqual(incoming["direction"], "incoming")
        self.assertEqual(APIClient().get(reverse("game-home")).status_code, 401)

    def test_letter_state_and_access(self) -> None:
        url = reverse("game-letter", args=[self.letter.id])
        self.assertEqual(self.guest_api.get(url).data["game"]["plays_left"], 3)
        stranger = client_for(make_user("별빛", region("부산", "해운대구")))
        self.assertEqual(stranger.get(url).status_code, 404)
        self.assertEqual(self.start(stranger, self.letter.id).status_code, 404)
        Block.objects.create(blocker=self.host, blocked=self.guest)
        self.assertEqual(self.guest_api.get(url).status_code, 404)

    def test_practice_run(self) -> None:
        response = self.start(self.guest_api)
        self.assertEqual(response.status_code, 201, response.data)
        run = response.data
        self.assertTrue(run["practice"])
        self.assertIsNone(run["letter_id"])
        self.assertEqual(run["reducible_seconds"], 0)
        self.assertEqual(run["piece_total"], count_kind(run["course"], PIECE))
        self.assertEqual(run["today_remaining"], 9)
        result = self.finish(self.guest_api, run["id"], run["piece_total"], 0).data
        self.assertEqual((result["stars"], result["reduced_seconds"]), (3, 0))
        self.assertTrue(result["perfect"])
        self.assertIsNone(result["letter"])
        self.assertEqual(
            {s["code"] for s in result["granted_stamps"]},
            {"star-candy", "strawberry-cat", "rainbow-letter"},
        )

    def test_reduce_arrival(self) -> None:
        before = self.letter.arrives_at
        result = self.play(self.guest_api, 2, self.letter.id)
        self.assertEqual(result["reduced_seconds"], 20 * 60)
        self.letter.refresh_from_db()
        self.assertEqual(self.letter.arrives_at, before - timedelta(minutes=20))
        self.assertEqual(result["letter"]["reduced_total_seconds"], 20 * 60)
        # 받는 사람도 같은 편지로 줄일 수 있다
        result = self.play(self.host_api, 3, self.letter.id)
        self.assertEqual(result["reduced_seconds"], 30 * 60)
        self.letter.refresh_from_db()
        self.assertEqual(self.letter.arrives_at, before - timedelta(minutes=50))
        self.assertEqual(self.letter.duration_minutes, 360)

    def test_failed_run_keeps_arrival(self) -> None:
        before = self.letter.arrives_at
        result = self.play(self.guest_api, 0, self.letter.id)
        self.assertFalse(result["success"])
        self.assertEqual(result["granted_stamps"], [])
        self.letter.refresh_from_db()
        self.assertEqual(self.letter.arrives_at, before)

    def test_reduce_cap(self) -> None:
        # 1시간 편지(같은 시·도)는 30분까지만 줄어든다
        neighbor = make_user("별빛", region("서울", "종로구"), hometown=region("서울"))
        sent = send(self.guest_api, diary_id=make_diary(neighbor).id)
        letter = Letter.objects.get(id=sent.data["id"])
        self.assertEqual(letter.duration_minutes, 60)
        self.assertEqual(self.play(self.guest_api, 2, letter.id)["reduced_seconds"], 1200)
        self.assertEqual(self.play(self.guest_api, 2, letter.id)["reduced_seconds"], 600)
        response = self.start(client_for(neighbor), letter.id)
        self.assertEqual((response.status_code, response.data["code"]), (409, "REDUCE_LIMIT"))

    def test_floor_near_arrival(self) -> None:
        Letter.objects.filter(id=self.letter.id).update(
            arrives_at=timezone.now() + timedelta(minutes=12)
        )
        run = self.start(self.guest_api, self.letter.id).data
        Letter.objects.filter(id=self.letter.id).update(
            arrives_at=timezone.now() + timedelta(minutes=11)
        )
        result = self.finish(self.guest_api, run["id"], run["piece_total"], 0).data
        # 30분을 받을 수 있어도 도착까지 1분은 남긴다
        self.assertAlmostEqual(result["reduced_seconds"], 10 * 60, delta=2)
        self.assertAlmostEqual(result["letter"]["remaining_seconds"], 60, delta=2)

    def test_letter_limits(self) -> None:
        for _ in range(3):
            self.play(self.guest_api, 1, self.letter.id)
        response = self.start(self.guest_api, self.letter.id)
        self.assertEqual((response.status_code, response.data["code"]), (409, "PLAY_LIMIT"))

        Letter.objects.filter(id=self.letter.id).update(
            arrives_at=timezone.now() + timedelta(minutes=5)
        )
        soon = self.start(self.host_api, self.letter.id)
        self.assertEqual((soon.status_code, soon.data["code"]), (409, "ARRIVING_SOON"))
        Letter.objects.filter(id=self.letter.id).update(arrives_at=timezone.now())
        arrived = self.start(self.host_api, self.letter.id)
        self.assertEqual((arrived.status_code, arrived.data["code"]), (409, "LETTER_ARRIVED"))

    def test_daily_limit(self) -> None:
        for _ in range(rules.DAILY_LIMIT):
            self.assertEqual(self.start(self.guest_api).status_code, 201)
        response = self.start(self.guest_api)
        self.assertEqual((response.status_code, response.data["code"]), (429, "DAILY_LIMIT"))
        self.assertEqual(self.guest_api.get(reverse("game-home")).data["today"]["remaining"], 0)

    def test_finish_validation(self) -> None:
        run = self.start(self.guest_api).data
        too_fast = self.finish(self.guest_api, run["id"], 1, 0, age=5)
        self.assertEqual((too_fast.status_code, too_fast.data["code"]), (400, "RUN_TOO_FAST"))
        too_many = self.finish(self.guest_api, run["id"], run["piece_total"] + 1, 0)
        self.assertEqual(too_many.status_code, 400)
        negative = self.finish(self.guest_api, run["id"], -1, 0)
        self.assertEqual(negative.status_code, 400)
        other = self.finish(self.host_api, run["id"], 1, 0)
        self.assertEqual(other.status_code, 404)
        self.assertEqual(self.finish(self.guest_api, run["id"], 1, 0).status_code, 200)
        again = self.finish(self.guest_api, run["id"], 1, 0)
        self.assertEqual((again.status_code, again.data["code"]), (409, "RUN_FINISHED"))

    def test_expired_and_abandoned(self) -> None:
        old = self.start(self.guest_api).data
        GameRun.objects.filter(id=old["id"]).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        expired = self.finish(self.guest_api, old["id"], 1, 0, age=rules.RUN_TTL_SECONDS + 10)
        self.assertEqual((expired.status_code, expired.data["code"]), (409, "RUN_EXPIRED"))
        self.assertEqual(GameRun.objects.get(id=old["id"]).status, "expired")

        first = self.start(self.guest_api).data
        self.start(self.guest_api)
        abandoned = self.finish(self.guest_api, first["id"], 1, 0)
        self.assertEqual((abandoned.status_code, abandoned.data["code"]), (409, "RUN_EXPIRED"))

    def test_stamp_goals(self) -> None:
        self.play(self.guest_api, 1)
        self.assertIn("star-candy", owned_codes(self.guest))
        self.assertNotIn("strawberry-cat", owned_codes(self.guest))
        result = self.play(self.guest_api, 3)
        self.assertEqual([s["code"] for s in result["granted_stamps"]], ["strawberry-cat"])
        for _ in range(3):
            self.play(self.guest_api, 3)
        owned = owned_codes(self.guest)
        self.assertTrue({"cloud-bread", "tulip"} <= owned)
        self.assertNotIn("little-whale", owned)
        self.assertEqual(progress(self.guest)["successes"], 5)
        goal = next(
            g
            for g in self.guest_api.get(reverse("game-home")).data["goals"]
            if g["stamp"]["code"] == "tangerine"
        )
        self.assertEqual((goal["progress"], goal["target"], goal["owned"]), (5, 10, False))

    def test_far_letter_stamp(self) -> None:
        jeju = make_user("귤껍질", region("제주", "제주시"), hometown=region("서울"))
        sent = send(self.guest_api, diary_id=make_diary(jeju).id)
        letter = Letter.objects.get(id=sent.data["id"])
        self.assertEqual(letter.band, "far")
        self.play(self.guest_api, 3, letter.id)
        self.assertIn("little-whale", owned_codes(self.guest))

    def test_unlocked_rewards(self) -> None:
        # 가입 우표 + 첫 편지 우표 = 2개. 게임 우표 1개로 3개가 되면 스티커가 열린다
        result = self.play(self.guest_api, 1)
        self.assertEqual([r["code"] for r in result["unlocked_rewards"]], ["stickers-cat"])


@override_settings(LETTER_DEMO_MODE=True)
class DemoModeTests(TestCase):
    def test_seconds_in_demo_mode(self) -> None:
        host = make_user("하늘빛", region("충남", "천안시"), hometown=region("서울"))
        guest = make_user("다인", region("서울", "성북구"), hometown=region("충남", "천안시"))
        api = client_for(guest)
        sent = send(api, diary_id=make_diary(host).id)
        letter = Letter.objects.get(id=sent.data["id"])
        self.assertEqual(letter.duration_minutes, 1)
        state = api.get(reverse("game-letter", args=[letter.id])).data["game"]
        self.assertEqual(state["max_reduce_seconds"], 30)
        run = api.post(reverse("game-run-start"), {"letter_id": letter.id}, "json").data
        GameRun.objects.filter(id=run["id"]).update(
            started_at=timezone.now() - timedelta(seconds=26)
        )
        Letter.objects.filter(id=letter.id).update(
            arrives_at=timezone.now() + timedelta(seconds=40)
        )
        result = api.post(
            reverse("game-run-finish", args=[run["id"]]),
            {"pieces": run["piece_total"], "hits": 0},
            "json",
        ).data
        # 별 3개 = 30초, 상한 30초
        self.assertEqual(result["reduced_seconds"], 30)
