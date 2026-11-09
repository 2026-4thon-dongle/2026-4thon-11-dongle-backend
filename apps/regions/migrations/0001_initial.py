import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="Region",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=20)),
                ("short_name", models.CharField(blank=True, max_length=10)),
                ("kind", models.CharField(choices=[("sido", "시·도"), ("sigungu", "시·군·구")], max_length=10)),
                ("is_metropolitan", models.BooleanField(default=False)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="regions.region")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddConstraint(
            model_name="region",
            constraint=models.UniqueConstraint(fields=("parent", "name"), name="uniq_region_parent_name"),
        ),
    ]
