# Generated by Django 4.0.7 on 2022-10-25 14:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0006_collectionvote"),
    ]

    operations = [
        migrations.CreateModel(
            name="DiscordUser",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("discord_tag", models.CharField(max_length=100)),
                ("avatar", models.CharField(max_length=100)),
                ("public_flags", models.IntegerField()),
                ("flags", models.IntegerField()),
                ("locale", models.CharField(max_length=100)),
                ("mfa_enabled", models.BooleanField()),
                ("raw_response_data", models.JSONField()),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]