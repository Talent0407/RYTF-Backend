from django.core.management.base import BaseCommand

from ryft.core.tasks import fetch_collection_price_history


class Command(BaseCommand):
    def handle(self, *args, **options):
        # This is being used as a cronjob - do not edit this command
        fetch_collection_price_history.delay()
