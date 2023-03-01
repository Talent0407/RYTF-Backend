from django.core.management.base import BaseCommand

from ryft.core.tasks import create_nft_attributes


class Command(BaseCommand):
    def handle(self, *args, **options):
        contract_address = ""
        create_nft_attributes(contract_address)
