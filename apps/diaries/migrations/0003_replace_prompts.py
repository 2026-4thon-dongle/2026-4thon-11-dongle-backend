from django.db import migrations

# 2026-11-11 Figma 메모의 확정 글감 14개 (문서 레포 screens/02_first-diary.md)
PROMPTS = [
    "우리 동네 사람이면 다 아는 장소는?",
    "요즘 우리 동네에서 제일 맛있는 한 끼는?",
    "오늘 등굣길에 본 풍경 하나",
    "자취방 창문 밖으로 뭐가 보여요?",
    "우리 동네 단골 가게를 소개해 주세요",
    "친구가 놀러 오면 꼭 데려가고 싶은 곳은?",
    "요즘 우리 동네 날씨는 어때요?",
    "나만 아는 동네 산책 코스",
    "이 동네에 와서 처음 해본 것",
    "시험기간에 찾는 나만의 공부 스팟",
    "이번 계절, 우리 동네에서만 볼 수 있는 것",
    "동네 시장 · 편의점에서 꼭 사는 것",
    "오늘 고향 생각이 났던 순간",
    "고향 친구한테 자랑하고 싶은 우리 동네 한 가지",
]


def replace(apps, schema_editor):
    # 기존 글감은 지우지 않고 끈다. 주간 글감 알림의 target_id가 글감 id를 가리킨다.
    prompt_model = apps.get_model("diaries", "DiaryPrompt")
    prompt_model.objects.exclude(text__in=PROMPTS).update(is_active=False)
    existing = set(prompt_model.objects.filter(text__in=PROMPTS).values_list("text", flat=True))
    prompt_model.objects.bulk_create(
        prompt_model(text=text) for text in PROMPTS if text not in existing
    )


def restore(apps, schema_editor):
    prompt_model = apps.get_model("diaries", "DiaryPrompt")
    prompt_model.objects.filter(text__in=PROMPTS).delete()
    prompt_model.objects.update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [("diaries", "0002_seed_prompts")]

    operations = [migrations.RunPython(replace, restore)]
