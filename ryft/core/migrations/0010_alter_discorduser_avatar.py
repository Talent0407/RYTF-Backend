# Generated by Django 4.0.8 on 2022-11-23 20:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_alter_usertrackedwallet_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="discorduser",
            name="avatar",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
