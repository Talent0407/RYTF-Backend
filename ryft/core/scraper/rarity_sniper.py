import csv
import random
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as BraveService
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType


class RaritySniperScraper:
    def export(self, field_names: list, data: list):
        """
        :param field_names: list of collection objects names
        :param data: list of collection objects
        :return:
        """
        with open("rarity_sniper_collections.csv", "w") as f:
            writer = csv.DictWriter(f, fieldnames=field_names)
            writer.writeheader()
            writer.writerows(data)

    def scroll_until_bottom(self, driver):
        SCROLL_PAUSE_TIME = 60 * 5
        time.sleep(SCROLL_PAUSE_TIME)

        # Get scroll height
        # last_height = driver.execute_script("return document.body.scrollHeight")
        # while True:
        #     # Scroll down to bottom
        #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        #
        #     # Wait to load page
        #     time.sleep(SCROLL_PAUSE_TIME)
        #
        #     # Calculate new scroll height and compare with last scroll height
        #     new_height = driver.execute_script("return document.body.scrollHeight")
        #     if new_height == last_height:
        #         break
        #     last_height = new_height
        #     print("Scrolling again")
        #
        print("Reached bottom")

    def get_browser(self):
        options = Options()
        options.binary_location = (
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
        )
        browser = webdriver.Chrome(
            options=options,
            service=BraveService(
                ChromeDriverManager(chrome_type=ChromeType.BRAVE).install()
            ),
        )
        return browser

    def get_collections(self):
        url = "https://raritysniper.com/nft-collections?blockchain=ethereum&totalVolume=1:&sort=marketCap:desc"

        browser = self.get_browser()
        browser.get(url)
        self.scroll_until_bottom(browser)

        collections = []
        collection_results = browser.find_elements(
            by=By.XPATH, value="//div[@slot='hit']"
        )

        for result in collection_results:
            name_tag = result.find_element(by=By.TAG_NAME, value="h4")
            name = name_tag.text
            images = result.find_elements(by=By.TAG_NAME, value="img")
            a_tag = result.find_element(by=By.TAG_NAME, value="a")
            href = a_tag.get_attribute("href")

            image_url = None
            if images is not None:
                thumbnail = images[0]
                name = thumbnail.get_attribute("alt")

                image_url = thumbnail.get_attribute("src")

            collections.append({"Name": name, "Thumbnail": image_url, "Href": href})

        browser.close()

        return collections

    def get_link(self, links, name):
        link_filter = list(filter(lambda x: name in x, links))
        if len(link_filter) > 0:
            if len(link_filter) > 2:
                raise ValueError(f"{link_filter} returned more than 2 result")
            return link_filter[-1]
        return None

    def get_individual_collections(self):
        field_names = [
            "Href",
            "Supply",
            "OpenseaURL",
            "DiscordURL",
            "TwitterURL",
            "LooksrareURL",
            "PreviewImages",
        ]
        collections = []
        browser = self.get_browser()

        with open("collections.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                collection = self.get_collection(browser, row["Href"])
                collections.append(collection)
                self.export(field_names=field_names, data=collections)

        browser.close()

    def get_collection(self, browser, url):
        browser.get(url)
        time.sleep(5)

        supply_tag = browser.find_element(
            by=By.XPATH, value="//div[@class='ais-Stats']"
        )
        link_div = browser.find_element(
            by=By.XPATH, value="//div[@class='flex flex-wrap gap-10 flex-grow']"
        )
        link_tags = link_div.find_elements(by=By.TAG_NAME, value="a")
        links = []
        for link in link_tags:
            links.append(link.get_attribute("href"))

        links = list(set(links))

        opensea_url = self.get_link(links, "opensea")
        discord_url = self.get_link(links, "discord")
        twitter_url = self.get_link(links, "twitter")
        looksrare_url = self.get_link(links, "looksrare")

        preview_image_results = browser.find_elements(
            by=By.XPATH, value="//div[@data-cy='card-card-asset']"
        )

        preview_images = []
        for result in preview_image_results[0:2]:
            images = result.find_elements(by=By.TAG_NAME, value="img")
            image_url = None
            if images is not None:
                thumbnail = images[0]
                image_url = thumbnail.get_attribute("src")
            preview_images.append(image_url)

        collection = {
            "Href": url,
            "Supply": supply_tag.text,
            "OpenseaURL": opensea_url,
            "DiscordURL": discord_url,
            "TwitterURL": twitter_url,
            "LooksrareURL": looksrare_url,
            "PreviewImages": preview_images,
        }

        return collection

    def get_all_csv_data(self):
        collections = []
        collection_details = []
        with open("data/collections-duplicate.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                collections.append(
                    {
                        "Name": row["Name"],
                        "Thumbnail": row["Thumbnail"],
                        "Href": row["Href"],
                    }
                )

        with open("data/rarity_sniper_collections-duplicate.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                collection_details.append(
                    {
                        "Href": row["Href"],
                        "Supply": row["Supply"],
                        "OpenseaURL": row["OpenseaURL"],
                        "DiscordURL": row["DiscordURL"],
                        "TwitterURL": row["TwitterURL"],
                        "LooksrareURL": row["LooksrareURL"],
                        "PreviewImages": row["PreviewImages"],
                    }
                )
        return collections, collection_details

    def get_contract_address(self, collection):
        looksrare_url = collection.get("LooksrareURL")
        # https://looksrare.org/collections/0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d
        if not looksrare_url:
            return None
        url_split = looksrare_url.split("/")
        contract_address = url_split[-1]
        return contract_address

    def save_image_to_folder(self, filename, png):
        with open(
            f"ryft/media/scraped/collection_thumbnails/{filename}.png", "wb"
        ) as file:
            file.write(png)

    def download_images(self):
        url = "https://raritysniper.com/nft-collections?blockchain=ethereum&totalVolume=1:&sort=marketCap:desc"

        browser = self.get_browser()
        browser.get(url)
        # self.scroll_until_bottom(browser)
        # browser.implicitly_wait(3)
        time.sleep(60 * 4)

        collection_results = browser.find_elements(
            by=By.XPATH, value="//div[@slot='hit']"
        )

        for result in collection_results:
            images = result.find_elements(by=By.TAG_NAME, value="img")

            if images is not None:
                thumbnail = images[0]
                name = thumbnail.get_attribute("alt")
                try:
                    print(name)
                    self.save_image_to_folder(name, thumbnail.screenshot_as_png)
                except FileNotFoundError:
                    print(f"Couldn't save file {name}")

        browser.close()

        return

    def download_artwork_preview_images(self, url):
        print(url)
        browser = self.get_browser()
        browser.get(url)
        browser.implicitly_wait(10)

        nft_results = browser.find_elements(
            by=By.XPATH, value="//div[@class='mx-auto p-2 min-h-full']"
        )

        for result in nft_results:
            images = result.find_elements(by=By.TAG_NAME, value="img")

            if images is not None:
                first_preview = images[random.randint(0, 7)]
                second_preview = images[random.randint(7, 15)]

                preview_images = [first_preview, second_preview]
                for thumbnail in preview_images:
                    name = thumbnail.get_attribute("alt")
                    try:
                        full_name = f"previews/{name}.png"
                        print(full_name)
                        self.save_image_to_folder(
                            full_name, thumbnail.screenshot_as_png
                        )
                    except FileNotFoundError:
                        print(f"Couldn't save file {name}")

        browser.close()

        return
