import io
import shutil
import tempfile
from datetime import datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from apps.moderations.models import Block
from apps.stamps.models import RewardSeen, Stamp, UserStamp
from apps.users.models import User

from .delivery import ADJACENT, FAR, NEAR, SAME_SIDO, band_between, duration_minutes
from .models import Conversation, Letter
from .testing import arrive, client_for, make_diary, make_user, region, send

MEDIA = tempfile.mkdtemp()


def image(fmt: str = "PNG") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGBA" if fmt == "PNG" else "RGB", (4, 4)).save(buffer, fmt)
    return SimpleUploadedFile(f"s.{fmt.lower()}", buffer.getvalue(), content_type="image/png")


def give_stamps(user: User, count: int) -> None:
    owned = UserStamp.objects.filter(user=user).values("stamp_id")
    for stamp in Stamp.objects.exclude(id__in=owned).exclude(code="stamp-collector")[:count]:
        UserStamp.objects.create(user=user, stamp=stamp)


class DeliveryTests(TestCase):
    def test_bands(self) -> None:
        seongbuk, cheonan = region("서울", "성북구"), region("충남", "천안시")
        self.assertEqual(band_between(seongbuk, region("서울", "종로구")), SAME_SIDO)
        self.assertEqual(band_between(seongbuk, region("경기", "수원시")), ADJACENT)
        self.assertEqual(band_between(seongbuk, cheonan), NEAR)
        self.assertEqual(band_between(seongbuk, region("부산", "해운대구")), FAR)
        self.assertEqual(band_between(region("전남", "목포시"), region("제주", "제주시")), FAR)
        self.assertEqual(band_between(region("세종"), cheonan), ADJACENT)

    def test_durations(self) -> None:
        self.assertEqual(
            [duration_minutes(b) for b in (SAME_SIDO, ADJACENT, NEAR, FAR)], [60, 180, 360, 720]
        )
        with override_settings(LETTER_DEMO_MODE=True):
            self.assertEqual(duration_minutes(FAR), 1)


class MaterialsTests(TestCase):
    def setUp(self) -> None:
        self.user = make_user("재민", region("서울", "성북구"))
        self.api = client_for(self.user)

    def test_locked_items(self) -> None:
        data = self.api.get(reverse("letter-materials")).data
        night = next(s for s in data["stationeries"] if s["code"] == "night-sky")
        self.assertEqual((night["unlocked"], night["unlock_condition"]), (False, "우표 5개"))
        self.assertTrue(data["stationeries"][0]["unlocked"])
        self.assertFalse(any(s["unlocked"] for s in data["stickers"]))
        self.assertEqual([s["code"] for s in data["stamps"]], ["first-step"])

    def test_unlocked_is_new_until_seen(self) -> None:
        give_stamps(self.user, 4)
        night = next(
            s
            for s in self.api.get(reverse("letter-materials")).data["stationeries"]
            if s["code"] == "night-sky"
        )
        self.assertTrue(night["unlocked"] and night["is_new"])
        RewardSeen.objects.create(user=self.user, code="stationery-night-sky")
        night = next(
            s
            for s in self.api.get(reverse("letter-materials")).data["stationeries"]
            if s["code"] == "night-sky"
        )
        self.assertFalse(night["is_new"])


@override_settings(MEDIA_ROOT=MEDIA)
class SendTests(TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self) -> None:
        self.host = make_user("하늘빛", region("충남", "천안시"))
        self.guest = make_user("다인", region("서울", "성북구"), hometown=region("충남", "천안시"))
        self.diary = make_diary(self.host)
        self.guest_client = client_for(self.guest)
        self.host_client = client_for(self.host)

    def test_requires_login(self) -> None:
        self.assertEqual(APIClient().post(reverse("letter-send"), {}).status_code, 401)

    def test_estimate(self) -> None:
        data = self.guest_client.get(reverse("letter-estimate"), {"diary_id": self.diary.id}).data
        self.assertEqual((data["band"], data["duration_minutes"]), (NEAR, 360))
        self.assertEqual(data["from_region"]["sido"], "서울")
        self.assertEqual(data["to_region"]["full_name"], "충남 천안시")
        self.assertEqual(self.guest_client.get(reverse("letter-estimate")).status_code, 400)
        missing = self.guest_client.get(reverse("letter-estimate"), {"diary_id": 999})
        self.assertEqual(missing.status_code, 404)

    def test_first_letter(self) -> None:
        # 실행 시각이 새벽(0~5시)이면 새벽 우표가 같이 나가므로 낮 시각으로 고정한다.
        noon = datetime(2026, 11, 14, 12, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        with mock.patch("apps.letters.services.timezone.now", return_value=noon):
            response = send(self.guest_client, diary_id=self.diary.id)
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data
        self.assertTrue(data["is_first"])
        self.assertEqual(data["recipient"]["nickname"], "하늘빛")
        self.assertEqual((data["band"], data["duration_minutes"]), (NEAR, 360))
        self.assertEqual(data["arrives_at"] - data["sent_at"], timedelta(minutes=360))
        self.assertEqual([s["code"] for s in data["granted_stamps"]], ["first-letter"])
        conversation = Conversation.objects.get()
        self.assertEqual((conversation.host, conversation.guest), (self.host, self.guest))
        self.assertEqual(Letter.objects.get().sender_nickname, "다인")

        again = send(self.guest_client, diary_id=self.diary.id)
        self.assertEqual((again.status_code, again.data["code"]), (409, "ALREADY_SENT"))

    def test_first_letter_rules(self) -> None:
        own = send(self.host_client, diary_id=self.diary.id)
        self.assertEqual((own.status_code, own.data["code"]), (403, "OWN_DIARY"))

        closed = make_diary(self.host, accepts_letters=False)
        off = send(self.guest_client, diary_id=closed.id)
        self.assertEqual((off.status_code, off.data["code"]), (403, "LETTERS_OFF"))

        self.host.letter_paused = True
        self.host.save()
        paused = send(self.guest_client, diary_id=self.diary.id)
        self.assertEqual((paused.status_code, paused.data["code"]), (403, "RECIPIENT_PAUSED"))
        self.host.letter_paused = False
        self.host.save()

        Block.objects.create(blocker=self.host, blocked=self.guest)
        blocked = send(self.guest_client, diary_id=self.diary.id)
        self.assertEqual(blocked.status_code, 404)

    def test_validation(self) -> None:
        both = send(self.guest_client, diary_id=self.diary.id, reply_to=1)
        self.assertEqual(both.status_code, 400)
        blank = send(self.guest_client, diary_id=self.diary.id, body="   ")
        self.assertEqual(blank.status_code, 400)
        long = send(self.guest_client, diary_id=self.diary.id, body="가" * 1001)
        self.assertEqual(long.status_code, 400)

    def test_locked_items(self) -> None:
        paper = send(self.guest_client, diary_id=self.diary.id, stationery="night-sky")
        self.assertEqual((paper.status_code, paper.data["code"]), (400, "ITEM_LOCKED"))
        stamp = send(self.guest_client, diary_id=self.diary.id, stamp="tulip")
        self.assertEqual((stamp.status_code, stamp.data["code"]), (400, "ITEM_LOCKED"))
        sticker = [{"code": "cat-wink", "x": 0.5, "y": 0.5}]
        locked = send(self.guest_client, diary_id=self.diary.id, stickers=sticker)
        self.assertEqual((locked.status_code, locked.data["code"]), (400, "ITEM_LOCKED"))
        give_stamps(self.guest, 2)
        ok = send(self.guest_client, diary_id=self.diary.id, stickers=sticker)
        self.assertEqual(ok.status_code, 201, ok.data)
        self.assertEqual(Letter.objects.get().stickers[0]["code"], "cat-wink")

    def test_signature_and_stickers_multipart(self) -> None:
        give_stamps(self.guest, 2)
        response = send(
            self.guest_client,
            fmt="multipart",
            diary_id=self.diary.id,
            signature=image(),
            stickers='[{"code": "cat-smile", "x": 0.2, "y": 0.9, "rotation": 5}]',
        )
        self.assertEqual(response.status_code, 201, response.data)
        letter = Letter.objects.get()
        self.assertTrue(str(letter.signature.name).startswith("signatures/"))
        self.assertEqual(letter.stickers[0]["rotation"], 5)
        jpeg = send(
            self.guest_client,
            fmt="multipart",
            diary_id=make_diary(self.host).id,
            signature=image("JPEG"),
        )
        self.assertEqual(jpeg.status_code, 400)

    def test_times_are_korea_time(self) -> None:
        estimate = self.guest_client.get(reverse("letter-estimate"), {"diary_id": self.diary.id})
        self.assertRegex(estimate.json()["arrives_at"], r"\+09:00$")
        sent = send(self.guest_client, diary_id=self.diary.id)
        body = sent.json()
        self.assertRegex(body["sent_at"], r"\+09:00$")
        self.assertRegex(body["arrives_at"], r"\+09:00$")
        arrive(body["id"])
        detail = self.host_client.get(reverse("letter-detail", args=[body["id"]])).json()
        self.assertRegex(detail["sent_at"], r"\+09:00$")
        self.assertRegex(detail["arrived_at"], r"\+09:00$")
        self.assertNotIn("Z", body["sent_at"] + detail["arrived_at"])

    def test_sticker_scale(self) -> None:
        give_stamps(self.guest, 2)
        sticker = {"code": "cat-wink", "x": 0.5, "y": 0.5, "rotation": -8}
        response = send(
            self.guest_client,
            diary_id=self.diary.id,
            stickers=[{**sticker, "scale": 0.3}, sticker],
        )
        self.assertEqual(response.status_code, 201, response.data)
        letter = Letter.objects.get()
        self.assertEqual([s["scale"] for s in letter.stickers], [0.3, 0.18])
        arrive(letter.id)
        detail = self.host_client.get(reverse("letter-detail", args=[letter.id])).data
        self.assertEqual([s["scale"] for s in detail["stickers"]], [0.3, 0.18])

    def test_sticker_scale_legacy_default(self) -> None:
        give_stamps(self.guest, 2)
        send(self.guest_client, diary_id=self.diary.id)
        letter = Letter.objects.get()
        letter.stickers = [{"code": "cat-wink", "x": 0.1, "y": 0.2, "rotation": 0}]
        letter.save()
        arrive(letter.id)
        detail = self.host_client.get(reverse("letter-detail", args=[letter.id])).data
        self.assertEqual(detail["stickers"][0]["scale"], 0.18)

    def test_sticker_scale_out_of_range(self) -> None:
        give_stamps(self.guest, 2)
        for scale in (0, 0.02, 0.51, 1.5, -0.1, "big", "nan"):
            response = send(
                self.guest_client,
                diary_id=self.diary.id,
                stickers=[{"code": "cat-wink", "x": 0.5, "y": 0.5, "scale": scale}],
            )
            self.assertEqual(response.status_code, 400, scale)
            self.assertEqual(response.data["code"], "VALIDATION_ERROR", scale)
        self.assertFalse(Letter.objects.exists())

    def test_sticker_bad_code_or_number_is_validation_error(self) -> None:
        give_stamps(self.guest, 2)
        bad_stickers = [
            {"code": ["cat-wink"], "x": 0.5, "y": 0.5},
            {"code": {"a": 1}, "x": 0.5, "y": 0.5},
            {"code": 3, "x": 0.5, "y": 0.5},
            {"code": "cat-wink", "x": 0.5, "y": 0.5, "rotation": "nan"},
            {"code": "cat-wink", "x": 0.5, "y": 0.5, "rotation": "inf"},
            {"code": "cat-wink", "x": 0.5, "y": 0.5, "rotation": "-Infinity"},
        ]
        for sticker in bad_stickers:
            response = send(self.guest_client, diary_id=self.diary.id, stickers=[sticker])
            self.assertEqual(response.status_code, 400, sticker)
            self.assertEqual(response.data["code"], "VALIDATION_ERROR", sticker)
        self.assertFalse(Letter.objects.exists())

    def test_reply_round_trip(self) -> None:
        first = send(self.guest_client, diary_id=self.diary.id).data
        early = send(self.host_client, reply_to=first["id"])
        self.assertEqual((early.status_code, early.data["code"]), (409, "NOT_ARRIVED"))

        arrive(first["id"])
        reply = send(self.host_client, reply_to=first["id"])
        self.assertEqual(reply.status_code, 201, reply.data)
        self.assertFalse(reply.data["is_first"])
        self.assertEqual(reply.data["conversation_id"], first["conversation_id"])
        self.assertIn("first-roundtrip", [s["code"] for s in reply.data["granted_stamps"]])
        guest_stamp = UserStamp.objects.get(user=self.guest, stamp__code="first-roundtrip")
        self.assertEqual(guest_stamp.granted_with, self.host)

        again = send(self.host_client, reply_to=first["id"])
        self.assertEqual((again.status_code, again.data["code"]), (409, "ALREADY_REPLIED"))
        not_mine = send(self.guest_client, reply_to=first["id"])
        self.assertEqual(not_mine.status_code, 404)

    def test_closed_conversation(self) -> None:
        first = send(self.guest_client, diary_id=self.diary.id).data
        arrive(first["id"], ago=timedelta(days=8))
        late = send(self.host_client, reply_to=first["id"])
        self.assertEqual((late.status_code, late.data["code"]), (409, "CONVERSATION_CLOSED"))

        second = send(self.guest_client, diary_id=make_diary(self.host).id).data
        arrive(second["id"])
        Conversation.objects.filter(id=second["conversation_id"]).update(
            passed_at=datetime.now(ZoneInfo("Asia/Seoul"))
        )
        passed = send(self.host_client, reply_to=second["id"])
        self.assertEqual(passed.data["code"], "CONVERSATION_CLOSED")

    def test_penpal_after_three_round_trips(self) -> None:
        letter = send(self.guest_client, diary_id=self.diary.id).data
        clients = [self.host_client, self.guest_client]
        for turn in range(5):
            arrive(letter["id"])
            letter = send(clients[turn % 2], reply_to=letter["id"]).data
        self.assertTrue(
            UserStamp.objects.filter(user=self.guest, stamp__code="penpal-friend").exists()
        )
        self.assertTrue(
            UserStamp.objects.filter(user=self.host, stamp__code="penpal-friend").exists()
        )

    def test_condition_stamps(self) -> None:
        busan_host = make_user("갈매기", region("부산", "해운대구"))
        far_diary = make_diary(busan_host)
        dawn = datetime(2026, 11, 14, 3, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        with mock.patch("apps.letters.services.timezone.now", return_value=dawn):
            response = send(self.guest_client, diary_id=far_diary.id)
        codes = {s["code"] for s in response.data["granted_stamps"]}
        self.assertEqual(response.data["band"], FAR)
        self.assertTrue({"first-letter", "dawn-letter", "long-delivery"} <= codes)

    def test_unlocked_rewards_in_response(self) -> None:
        give_stamps(self.guest, 1)  # 2개 보유 → 첫 편지로 3개
        data = send(self.guest_client, diary_id=self.diary.id).data
        self.assertEqual([r["code"] for r in data["unlocked_rewards"]], ["stickers-cat"])
        self.assertFalse(data["unlocked_rewards"][0]["seen"])

    @override_settings(LETTER_DEMO_MODE=True)
    def test_demo_mode(self) -> None:
        data = send(self.guest_client, diary_id=self.diary.id).data
        self.assertEqual(data["duration_minutes"], 1)
        self.assertEqual(data["band"], NEAR)
