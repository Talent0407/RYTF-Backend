from django.core.management.base import BaseCommand

from ryft.core.integrations.alchemy import get_alchemy_client


class Command(BaseCommand):
    def handle(self, *args, **options):
        c = get_alchemy_client()
        c.create_webhook_address("0x94a465183ff9a939295d3c8cc09b5ca27a63fb9c")
