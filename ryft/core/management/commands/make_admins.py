from django.core.management.base import BaseCommand
from siwe_auth.models import Wallet

from config.settings.base import ADMIN_WALLETS


class Command(BaseCommand):
    def handle(self, *args, **options):

        user_wallets = Wallet.objects.filter(ethereum_address__in=ADMIN_WALLETS)
        print(user_wallets.values("ethereum_address", "is_admin", "is_superuser"))
        user_wallets.update(is_admin=True, is_superuser=True)
