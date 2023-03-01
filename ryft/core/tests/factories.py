import datetime
import random

import factory.fuzzy
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.utils.timezone import make_aware
from factory import Faker, LazyAttribute, SubFactory
from factory.django import DjangoModelFactory, ImageField

from ryft.core.models import (
    NFT,
    Collection,
    Transaction,
    Wallet,
    WalletNFT,
    WalletPortfolioRecord,
)
from ryft.users.tests.factories import UserFactory


def random_date(start, end):
    """Generate a random datetime between `start` and `end`"""
    return start + datetime.timedelta(
        # Get a random amount of seconds between `start` and `end`
        seconds=random.randint(0, int((end - start).total_seconds())),
    )


class CollectionFactory(DjangoModelFactory):
    name = Faker("name")
    description = Faker("sentence")
    contract_abi = Faker("sentence")
    supply = Faker("random_int")
    mint_date = Faker("date")
    mint_price = str(Faker("random_int"))
    released = factory.fuzzy.FuzzyChoice(choices=[True, True, True, False])
    verified = factory.fuzzy.FuzzyChoice(choices=[True, True, True, False])
    discord_link = Faker("url")
    twitter_link = Faker("url")
    website_link = Faker("url")
    opensea_link = Faker("url")
    num_discord_members = Faker("random_int")
    num_twitter_followers = Faker("random_int")
    thumbnail = LazyAttribute(
        lambda _: ContentFile(
            ImageField()._make_data({"width": 1024, "height": 768}), "example.jpg"
        )
    )

    class Meta:
        model = Collection

    @factory.lazy_attribute
    def contract_address(self):
        """Easier than generating fake address"""
        return slugify(str(self.name))


class WalletFactory(DjangoModelFactory):
    user = SubFactory(UserFactory)

    class Meta:
        model = Wallet

    @factory.lazy_attribute
    def wallet_address(self):
        """Easier than generating fake address"""
        return slugify(str(Faker("name")))


class WalletPortfolioRecordFactory(DjangoModelFactory):
    wallet = SubFactory(WalletFactory)
    portfolio_value = 10 * random.random()

    class Meta:
        model = WalletPortfolioRecord


class NFTFactory(DjangoModelFactory):
    collection = SubFactory(CollectionFactory)
    token_id = factory.fuzzy.FuzzyText(length=15)
    image_url = Faker("url")
    rarity_score = factory.fuzzy.FuzzyFloat(1, 100)
    rank = factory.fuzzy.FuzzyInteger(1, 10)
    buy_rank = factory.fuzzy.FuzzyInteger(1, 10)
    raw_metadata = {"cached_file_url": "example-url"}

    class Meta:
        model = NFT


class WalletNFTFactory(DjangoModelFactory):
    wallet = SubFactory(WalletFactory)
    nft = SubFactory(NFTFactory)
    nft_raw_data = {
        "title": "example title",
        "thumbnail_url": "https://thumbnail.com",
        "token_id": 1,
    }

    class Meta:
        model = WalletNFT


class TransactionFactory(DjangoModelFactory):
    wallet = SubFactory(WalletFactory)
    nft = SubFactory(NFTFactory)
    transaction_type = factory.fuzzy.FuzzyChoice(
        ["buy", "sell", "transfer_to", "transfer_from", "mint"]
    )
    transfer_from = factory.fuzzy.FuzzyText(length=15)
    transfer_to = factory.fuzzy.FuzzyText(length=15)
    contract_address = factory.fuzzy.FuzzyText(length=15)
    token_id = factory.fuzzy.FuzzyText(length=15)
    quantity = 1
    transaction_hash = factory.fuzzy.FuzzyText(length=15)
    block_hash = factory.fuzzy.FuzzyText(length=15)
    block_number = factory.fuzzy.FuzzyInteger(1, 10)
    raw_transaction_data = {
        "title": "example title",
        "thumbnail_url": "https://thumbnail.com",
    }
    price_eth = factory.fuzzy.FuzzyFloat(1, 100)
    price_usd = factory.fuzzy.FuzzyFloat(1000, 150000)
    transaction_date = make_aware(
        random_date(datetime.datetime(2016, 1, 1), datetime.datetime(2023, 1, 1))
    )

    class Meta:
        model = Transaction
