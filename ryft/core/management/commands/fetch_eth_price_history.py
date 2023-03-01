from django.core.management.base import BaseCommand

from ryft.core.tasks import fetch_eth_price_history


class Command(BaseCommand):
    def handle(self, *args, **options):
        fetch_eth_price_history()
