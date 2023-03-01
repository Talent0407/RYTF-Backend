from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        pass
        # client = mnemonic_client()
        # result = client.get_historical_collection_owners(
        #     "0x6023da5c4ed130e73cd816ec931b562db2c346bb"
        # )
        # print(result)
