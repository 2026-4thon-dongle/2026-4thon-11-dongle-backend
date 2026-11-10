from django.db import migrations


def seed(apps, schema_editor):
    stamp_model = apps.get_model("stamps", "Stamp")
    stamp_model.objects.create(code="first-step", number=1, name="첫 걸음", description="동글에 가입했어요")
    stamp_model.objects.create(code="first-diary", number=2, name="첫 일기", description="첫 고향 일기를 썼어요")


def unseed(apps, schema_editor):
    apps.get_model("stamps", "Stamp").objects.filter(number__in=[1, 2]).delete()


class Migration(migrations.Migration):
    dependencies = [("stamps", "0002_initial")]

    operations = [migrations.RunPython(seed, unseed)]
