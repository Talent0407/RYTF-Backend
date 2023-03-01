from django.core.management.base import BaseCommand

from ryft.core.portfolio.tasks import create_tracked_wallet


class Command(BaseCommand):
    def handle(self, *args, **options):
        create_tracked_wallet.delay(6)
