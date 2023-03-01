from django.core.management.base import BaseCommand

from ryft.core.models import NFT, Collection


class Command(BaseCommand):
    def handle(self, *args, **options):
        collections = Collection.objects.all().order_by("id")
        nfts_to_update = []

        for collection in collections:
            nfts = collection.nfts.all()

            for nft in nfts:
                # check the "image_url"
                if not nft.image_url:
                    # check the raw metadata
                    media = nft.raw_metadata.get("media")

                    if not media:
                        print(
                            f"NFT {nft.id} from collection {collection.id} media does not have media: {media}"
                        )

                    thumbnail = media[0].get("thumbnail")
                    raw_url = media[0].get("raw")

                    new_image_url = None

                    if thumbnail:
                        new_image_url = thumbnail
                    elif raw_url:
                        if "https" in raw_url:
                            new_image_url = raw_url
                    else:
                        print(f"NFT {nft.id} media does not have thumbnail: {media}")

                    nft.image_url = new_image_url
                    nfts_to_update.append(nft)

            NFT.objects.bulk_update(nfts_to_update, ["image_url"], batch_size=100)
            print(f"Completed {collection.id} {collection.name}")
