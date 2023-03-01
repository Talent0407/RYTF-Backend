from django.core.management.base import BaseCommand

from ryft.core.portfolio.tasks import fetch_collection_metrics


class Command(BaseCommand):
    def handle(self, *args, **options):
        # This is being used as a cronjob - do not edit this command
        fetch_collection_metrics.delay()
