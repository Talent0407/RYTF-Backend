from django.core.management.base import BaseCommand

from ryft.core.models import Collection, WalletNFT


class Command(BaseCommand):
    def handle(self, *args, **options):
        map = {}
        wallet_nfts = (
            WalletNFT.objects.filter(nft__isnull=False)
            .select_related("nft__collection")
            .all()
        )

        for wallet_nft in wallet_nfts:
            contract_address = wallet_nft.nft.collection.contract_address
            description = wallet_nft.nft.raw_metadata.get("description")
            if description:
                map[contract_address] = description

        updated_collections = []

        for contract_address in map.keys():
            collection = Collection.objects.filter(
                contract_address=contract_address
            ).first()
            if collection:
                if collection.description == "Todo":
                    collection.description = map[contract_address]
                    updated_collections.append(collection)

        Collection.objects.bulk_update(
            updated_collections, ["description"], batch_size=100
        )
