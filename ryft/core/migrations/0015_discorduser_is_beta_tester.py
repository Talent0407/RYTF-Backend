# Generated by Django 4.0.8 on 2023-01-14 13:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_alter_walletnft_nft"),
    ]

    operations = [
        migrations.AddField(
            model_name="discorduser",
            name="is_beta_tester",
            field=models.BooleanField(default=False),
        ),
    ]