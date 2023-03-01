from django.core.management.base import BaseCommand

from ryft.core.portfolio.tasks import send_daily_collection_email


class Command(BaseCommand):
    def handle(self, *args, **options):
        send_daily_collection_email.delay()
