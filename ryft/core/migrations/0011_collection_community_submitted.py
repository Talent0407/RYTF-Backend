# Generated by Django 4.0.8 on 2022-12-07 18:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_alter_discorduser_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="collection",
            name="community_submitted",
            field=models.BooleanField(default=False),
        ),
    ]
