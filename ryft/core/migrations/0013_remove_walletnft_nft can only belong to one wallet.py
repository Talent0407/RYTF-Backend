# Generated by Django 4.0.8 on 2023-01-02 13:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_collection_created_timestamp"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="walletnft",
            name="NFT can only belong to one Wallet",
        ),
    ]
