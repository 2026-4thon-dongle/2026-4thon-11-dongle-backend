from django.db import migrations

PROMPTS = [
    "오늘 동네에서 가장 먼저 눈에 들어온 풍경은?",
    "요즘 자주 가는 밥집을 소개해 주세요.",
    "이 동네의 오늘 날씨는 어땠나요?",
    "집으로 돌아오는 길에 본 것을 적어 주세요.",
    "이 동네에 와서 처음 먹어 본 음식이 있나요?",
    "동네에서 제일 좋아하는 산책길은 어디인가요?",
    "오늘 들은 동네 사람들의 말 한마디를 적어 주세요.",
    "고향 사람에게 이 동네의 어떤 곳을 보여 주고 싶나요?",
]


def seed(apps, schema_editor):
    prompt_model = apps.get_model("diaries", "DiaryPrompt")
    prompt_model.objects.bulk_create(prompt_model(text=text) for text in PROMPTS)


def unseed(apps, schema_editor):
    apps.get_model("diaries", "DiaryPrompt").objects.filter(text__in=PROMPTS).delete()


class Migration(migrations.Migration):
    dependencies = [("diaries", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
