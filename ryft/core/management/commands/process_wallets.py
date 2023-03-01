import time

from celery.result import AsyncResult
from django.core.management.base import BaseCommand

from ryft.core.models import Wallet
from ryft.core.portfolio.tasks import calculate_wallet_portfolio


class Command(BaseCommand):
    def handle(self, *args, **options):
        qs = Wallet.objects.filter(processed=False, id__gt=8).order_by("id")
        for wallet in qs:
            print(f"Performing tasks on wallet: {wallet.id}")
            result = calculate_wallet_portfolio(
                wallet.wallet_address, tracked_wallet=True
            )
            res = AsyncResult(result.task_id)
            while not res.successful():
                time.sleep(10)
