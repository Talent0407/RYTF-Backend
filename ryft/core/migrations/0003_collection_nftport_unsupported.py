# Generated by Django 4.0.7 on 2022-10-11 22:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_requestlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="collection",
            name="nftport_unsupported",
            field=models.BooleanField(default=False),
        ),
    ]