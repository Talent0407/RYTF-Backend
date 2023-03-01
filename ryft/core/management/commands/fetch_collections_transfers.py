from django.core.management.base import BaseCommand

from ryft.core.tasks import fetch_collections_transfers


class Command(BaseCommand):
    def handle(self, *args, **options):
        # This is being used as a cronjob - do not edit this command
        fetch_collections_transfers.delay()
