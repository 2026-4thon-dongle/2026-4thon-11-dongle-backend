"""우표 20종(업적 12 + 꾸미기 8). No.05~12와 꾸미기 등급은 화면에서 확인하지 못해 목록 순서·일반으로 둔다."""

from django.db import migrations

# (번호, 코드, 이름, 설명, 종류, 등급)
STAMPS = [
    (1, "first-step", "첫 걸음", "동글에 가입했어요", "achievement", "common"),
    (2, "first-diary", "첫 일기", "첫 고향 일기를 썼어요", "achievement", "common"),
    (3, "first-letter", "첫 편지", "첫 편지를 보냈어요", "achievement", "common"),
    (4, "first-roundtrip", "첫 왕복", "같은 사람과 편지를 한 번 주고받았어요", "achievement", "rare"),
    (5, "penpal-friend", "펜팔 친구", "펜팔 친구가 생겼어요", "achievement", "rare"),
    (6, "dawn-letter", "새벽 편지", "밤 12시~새벽 5시에 편지를 보냈어요", "achievement", "rare"),
    (7, "long-delivery", "먼 길 배달", "12시간 거리로 편지를 보냈어요", "achievement", "rare"),
    (8, "handwriting-master", "손글씨 장인", "손글씨 서명을 10번 남겼어요", "achievement", "rare"),
    (9, "first-snow", "첫눈 편지", "첫눈 오는 날 편지를 보냈어요", "achievement", "rare"),
    (10, "steady-letter", "꾸준한 편지", "4주 연속 편지를 보냈어요", "achievement", "common"),
    (11, "stamp-collector", "우표 수집가", "우표를 10개 모았어요", "achievement", "legendary"),
    (12, "cat-birthday", "고향이 생일", "고향이 생일을 함께 축하했어요", "achievement", "legendary"),
    (13, "strawberry-cat", "딸기 고양이", "시즌 이벤트에서 받았어요", "decoration", "common"),
    (14, "cloud-bread", "구름빵", "시즌 이벤트에서 받았어요", "decoration", "common"),
    (15, "star-candy", "별사탕", "시즌 이벤트에서 받았어요", "decoration", "common"),
    (16, "tulip", "튤립", "시즌 이벤트에서 받았어요", "decoration", "common"),
    (17, "little-whale", "꼬마 고래", "시즌 이벤트에서 받았어요", "decoration", "common"),
    (18, "tangerine", "제철 귤", "시즌 이벤트에서 받았어요", "decoration", "common"),
    (19, "bungeoppang", "붕어빵", "시즌 이벤트에서 받았어요", "decoration", "common"),
    (20, "rainbow-letter", "무지개 편지", "시즌 이벤트에서 받았어요", "decoration", "common"),
]


def seed(apps, schema_editor):
    stamp_model = apps.get_model("stamps", "Stamp")
    for number, code, name, description, kind, grade in STAMPS:
        stamp_model.objects.update_or_create(
            code=code,
            defaults={
                "number": number,
                "name": name,
                "description": description,
                "kind": kind,
                "grade": grade,
            },
        )


def unseed(apps, schema_editor):
    stamp_model = apps.get_model("stamps", "Stamp")
    stamp_model.objects.filter(number__gte=3).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("stamps", "0004_stamp_kind_grade_reward_seen"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
