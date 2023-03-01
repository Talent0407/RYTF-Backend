from django.core.management.base import BaseCommand

from ryft.core.models import Wallet
from ryft.core.portfolio.tasks import calculate_portfolio_total


class Command(BaseCommand):
    def handle(self, *args, **options):

        wallets = Wallet.objects.all()
        for wallet in wallets:
            calculate_portfolio_total(wallet.id)
