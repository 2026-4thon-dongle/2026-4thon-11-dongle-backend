from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('letters', '0003_draft'),
    ]

    operations = [
        migrations.CreateModel(
            name='DemoModeSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]