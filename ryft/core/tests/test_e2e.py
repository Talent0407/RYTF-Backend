import json
from unittest.mock import patch

import pytest

from ryft.core.api.serializers import (
    CollectionSerializer,
    NFTSerializer,
    WalletPortfolioRecordSerializer,
)
from ryft.core.models import Collection, Transaction, Wallet, WalletPortfolioRecord
from ryft.core.tests.factories import (
    CollectionFactory,
    NFTFactory,
    TransactionFactory,
    WalletFactory,
    WalletNFTFactory,
)

pytestmark = pytest.mark.django_db


class TestCollectionEndpoints:
    endpoint = "/api/collections/"

    def test_list(self, api_client, user):
        CollectionFactory.create_batch(3, released=True)
        client = api_client()
        client.force_authenticate(user=user)

        response = client.get(self.endpoint)

        assert response.status_code == 200
        assert len(json.loads(response.content)) == 3

    def test_retrieve(self, api_client, collection: Collection, user):
        expected_json = {
            "name": collection.name,
            "contract_address": collection.contract_address,
            "description": collection.description,
            "supply": collection.supply,
            "mint_date": collection.mint_date,
            "mint_price": collection.mint_price,
            "released": collection.released,
            "verified": collection.verified,
            "discord_link": collection.discord_link,
            "twitter_link": collection.twitter_link,
            "website_link": collection.website_link,
            "opensea_link": collection.opensea_link,
            "num_discord_members": collection.num_discord_members,
            "num_twitter_followers": collection.num_twitter_followers,
            "artwork_images": [],
            "thumbnail": "http://testserver"
            + CollectionSerializer(collection).data["thumbnail"],
        }
        url = f"{self.endpoint}{collection.contract_address}/"
        client = api_client()
        client.force_authenticate(user=user)

        response = client.get(url)

        assert response.status_code == 200
        assert json.loads(response.content) == expected_json

    def test_upcoming(self, api_client, user):
        CollectionFactory.create_batch(3, released=False)
        client = api_client()
        client.force_authenticate(user=user)

        response = client.get(f"{self.endpoint}upcoming/")

        assert response.status_code == 200
        assert len(json.loads(response.content)) == 3

    def test_nfts(self, api_client, user, collection):
        nfts = [
            NFTFactory(collection=collection, rank=1),
            NFTFactory(collection=collection, rank=2),
            NFTFactory(collection=collection, rank=3),
        ]
        expected_json = list(
            sorted(
                (
                    {
                        "contract_address": nft.collection.contract_address,
                        "token_id": nft.token_id,
                        "image_url": nft.image_url,
                        "rarity_score": nft.rarity_score,
                        "rank": nft.rank,
                        "buy_rank": nft.buy_rank,
                        "raw_metadata": nft.raw_metadata,
                    }
                    for nft in nfts
                ),
                key=lambda x: x["rank"],
            )
        )

        client = api_client()
        client.force_authenticate(user=user)

        url = f"/api/collections/{collection.contract_address}/nfts/"

        response = client.get(url)

        assert response.status_code == 200
        assert json.loads(response.content)["results"] == expected_json


class TestWalletEndpoints:
    endpoint = "/api/wallets/"

    def test_list(self, api_client, user):
        WalletFactory.create_batch(3, user=user)
        client = api_client()
        client.force_authenticate(user=user)

        response = client.get(self.endpoint)

        assert response.status_code == 200
        assert len(json.loads(response.content)) == 3

    def test_retrieve(self, api_client, user):
        wallet = WalletFactory(user=user)
        expected_json = {
            "wallet_address": wallet.wallet_address,
        }
        url = f"{self.endpoint}{wallet.wallet_address}/"
        client = api_client()
        client.force_authenticate(user=user)

        response = client.get(url)

        assert response.status_code == 200
        assert json.loads(response.content) == expected_json

    @patch("ryft.core.portfolio.tasks.calculate_wallet_portfolio", return_value=2.5)
    def test_create(self, mocked_calculate_wallet_portfolio, api_client, user):
        client = api_client()
        client.force_authenticate(user=user)

        valid_data_dict = {"wallet_address": "12345"}

        url = f"{self.endpoint}add/"

        response = client.post(url, valid_data_dict, format="json")

        assert response.status_code == 200
        assert json.loads(response.content) == valid_data_dict
        assert Wallet.objects.last().wallet_address

    def test_portfolio(
        self, api_client, user, wallet_portfolio_record: WalletPortfolioRecord
    ):
        wallet_address = wallet_portfolio_record.wallet.wallet_address
        client = api_client()
        client.force_authenticate(user=user)

        expected_json = [
            {
                "portfolio_value": wallet_portfolio_record.portfolio_value,
                "timestamp": WalletPortfolioRecordSerializer(
                    wallet_portfolio_record
                ).data["timestamp"],
            }
        ]
        url = f"{self.endpoint}{wallet_address}/portfolio/"
        response = client.get(url)

        assert response.status_code == 200
        assert json.loads(response.content) == expected_json

    def test_nfts(self, api_client, user):
        wallet = WalletFactory(user=user)
        wallet_nft = WalletNFTFactory(wallet=wallet)
        wallet_address = wallet_nft.wallet.wallet_address

        client = api_client()
        client.force_authenticate(user=user)

        expected_json = [
            {
                "id": wallet_nft.id,
                "nft": NFTSerializer(wallet_nft.nft).data,
                "nft_raw_data": {
                    "thumbnail_url": wallet_nft.nft_raw_data["thumbnail_url"],
                    "title": wallet_nft.nft_raw_data["title"],
                    "token_id": wallet_nft.nft_raw_data["token_id"],
                },
                "collection_thumbnail": CollectionSerializer(
                    wallet_nft.nft.collection
                ).data["thumbnail"],
                "token_floor_price": None,  # in this case because we aren't mocking a CollectionMetric instance
            }
        ]
        url = f"{self.endpoint}{wallet_address}/nfts/"
        response = client.get(url)

        assert response.status_code == 200
        assert json.loads(response.content)["results"] == expected_json

    def test_transactions(self, api_client, user, nft):
        wallet: Wallet = WalletFactory(user=user)
        transaction: Transaction = TransactionFactory(wallet=wallet, nft=nft)
        wallet_address = wallet.wallet_address

        client = api_client()
        client.force_authenticate(user=user)

        expected_json = [
            {
                "id": transaction.id,
                "nft": {
                    "cached_file_url": nft.raw_metadata["cached_file_url"],
                    "collection": {
                        "contract_address": nft.collection.contract_address,
                        "name": nft.collection.name,
                    },
                    "name": f"#{nft.token_id}",
                    "token_id": nft.token_id,
                },
                "transaction_type": transaction.transaction_type,
                "transfer_from": transaction.transfer_from,
                "transfer_to": transaction.transfer_to,
                "contract_address": transaction.contract_address,
                "token_id": transaction.token_id,
                "quantity": transaction.quantity,
                "transaction_hash": transaction.transaction_hash,
                "block_hash": transaction.block_hash,
                "block_number": transaction.block_number,
                "transaction_date": transaction.transaction_date.isoformat(),
                "price_eth": transaction.price_eth,
                "price_usd": transaction.price_usd,
            }
        ]

        url = f"{self.endpoint}{wallet_address}/transactions/"
        response = client.get(url)

        assert response.status_code == 200
        assert json.loads(response.content)["results"] == expected_json
