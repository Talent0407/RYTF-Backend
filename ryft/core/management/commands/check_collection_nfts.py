from django.core.management.base import BaseCommand
from django.db.models import Func, OuterRef

from ryft.core.models import Collection, CollectionAttribute


class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Collections without NFTs fetched
        """

        # Collections without thumbnails
        # collections_without_thumbnails = (
        #     Collection.objects
        #     .values("id", "name", "contract_address", "thumbnail")
        #     .order_by("id")
        # )
        #
        # for collection in collections_without_thumbnails:
        #     print(collection)

        # nft_count_subquery = (
        #     NFT.objects.filter(collection=OuterRef("id"))
        #     .order_by()
        #     .annotate(count=Func("id", function="Count"))
        #     .values("count")
        # )
        #
        # # Collections with count of NFTs
        # collections_without_nfts = (
        #     Collection.objects.select_related("nfts")
        #     .annotate(nft_count=nft_count_subquery)
        #     .filter(nft_count=0)
        #     .values("id", "name", "contract_address", "nft_count")
        #     .order_by("id")
        # )
        #
        # for collection in collections_without_nfts[0:20]:
        #     print(collection)

        """
        Collections without collection attributes
        """

        attributes_subquery = (
            CollectionAttribute.objects.filter(collection=OuterRef("id"))
            .order_by()
            .annotate(count=Func("id", function="Count"))
            .values("count")
        )

        # Collections with count of unranked NFTs
        collections = (
            Collection.objects.select_related("nfts")
            .annotate(attribute_count=attributes_subquery)
            .filter(attribute_count=0)
            .values("id", "name", "contract_address", "attribute_count")
            .order_by("id")
        )

        for collection in collections[0:50]:
            print(collection)
