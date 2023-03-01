from django.core.management.base import BaseCommand

from ryft.core.integrations.alchemy import get_alchemy_client
from ryft.core.models import Wallet


class Command(BaseCommand):
    help = "Creates a new notify webhook on Alchemy for wallet activity"

    def add_arguments(self, parser):
        parser.add_argument("webhook_url", type=str, help="Webhook URL (usually ngrok)")

    def handle(self, *args, **options):
        webhook_url = options["webhook_url"]
        wallet_addresses = list(Wallet.objects.values_list("wallet_address", flat=True))

        c = get_alchemy_client()
        response = c.create_notify_webhook(webhook_url, wallet_addresses)

        print(response.text)
