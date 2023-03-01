import csv
import urllib.request
from urllib.request import urlopen

from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.core.management.base import BaseCommand

from ryft.core.models import Collection
from ryft.core.scraper.rarity_sniper import RaritySniperScraper


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.save_collections_to_db()

    def save_collections_to_db(self):
        scraper = RaritySniperScraper()
        collections, collection_details = scraper.get_all_csv_data()

        # add collection basic info to the collection details
        length_collections = len(collections)

        def save_thumbnail(collection, thumbnail_url):
            img_temp = NamedTemporaryFile(delete=True)
            req = urllib.request.Request(
                thumbnail_url, headers={"User-Agent": "Magic Browser"}
            )
            img_temp.write(urlopen(req).read())
            img_temp.flush()
            collection.thumbnail.save(
                f"{collection.name} Thumbnail.png", File(img_temp)
            )

        def format_supply(raw_supply):
            # '20,000 items'
            raw_number = raw_supply.split(" ")[0].replace(",", "")
            return raw_number

        for i in range(0, length_collections):
            collection = collections[i]
            collection_details[i].update(**collection)
            collection_details[i]["contract_address"] = scraper.get_contract_address(
                collection_details[i]
            )

        for c in collection_details:
            contract_address = c["contract_address"]
            if contract_address:
                try:
                    print(f"Try collection {contract_address}")
                    collection = Collection.objects.get(
                        contract_address=c["contract_address"].lower()
                    )
                    # if not collection.thumbnail:
                    # add the thumbnail
                    save_thumbnail(collection, c["Thumbnail"])
                    print(f"Saved thumbnail to {contract_address}")

                except Collection.DoesNotExist:
                    collection = Collection.objects.create(
                        contract_address=c["contract_address"],
                        name=c["Name"],
                        description="Todo",
                        supply=format_supply(c["Supply"]),
                        released=True,
                        verified=True,
                        discord_link=c["DiscordURL"],
                        twitter_link=c["TwitterURL"],
                        opensea_link=c["OpenseaURL"],
                    )
                    print("Doesn't exist: ", collection.contract_address)

                    # website_link=c[""], # TODO
                    # num_discord_members=c[""],  # TODO
                    # num_twitter_followers=c[""],  # TODO

    def store_collection_thumbnails(self):
        scraper = RaritySniperScraper()
        scraper.download_images()

    def store_collection_artwork_previews(self):
        scraper = RaritySniperScraper()
        with open("data/collections_details.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row["Href"]
                scraper.download_artwork_preview_images(url)
                break
