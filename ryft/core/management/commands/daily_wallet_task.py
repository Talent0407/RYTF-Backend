from django.core.management.base import BaseCommand

from ryft.core.portfolio.tasks import daily_wallet_task


class Command(BaseCommand):
    def handle(self, *args, **options):
        # This is being used as a cronjob - do not edit this command
        daily_wallet_task()
