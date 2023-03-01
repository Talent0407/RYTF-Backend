import requests
from django.conf import settings
from requests_ratelimiter import LimiterSession
from retry import retry

from .errors import (
    AlchemyCollectionNFTsError,
    AlchemyFloorPriceError,
    AlchemyRateLimitError,
    AlchemyWalletNFTsError,
)


class AlchemyClient:
    """
    Client for implementing API calls to Alchemy service
    """

    def __init__(self):
        self.api_key = settings.ALCHEMY_API_KEY
        self.auth_token = settings.ALCHEMY_AUTH_TOKEN
        self._url = f"https://eth-mainnet.alchemyapi.io/nft/v2/{self.api_key}"
        self._dashboard_url = "https://dashboard.alchemyapi.io/api"
        # TODO monitor this because in the future there will be higher rate limits
        self.session = LimiterSession(per_second=25)
        self.alchemy_session = LimiterSession(per_second=3)

    def get_nfts_for_wallet(self, wallet_address, page=None):
        params = {"owner": wallet_address, "pageKey": page}
        response = self.session.get(f"{self._url}/getNFTs/", params=params)
        data = response.json()

        if data.get("error", None):
            raise AlchemyWalletNFTsError

        return data

    def get_nfts_for_collection(self, contract_address, start_token=None):
        params = {
            "contractAddress": contract_address,
            "withMetadata": True,
            "startToken": start_token,
            "limit": 100,
            "tokenUriTimeoutInMs": 0,
        }
        headers = {"Accept": "application/json"}
        response = self.session.get(
            f"{self._url}/getNFTsForCollection", params=params, headers=headers
        )
        data = response.json()

        if data.get("error", None):
            raise AlchemyCollectionNFTsError

        return data

    def get_floor_price(self, contract_address):
        params = {
            "contractAddress": contract_address,
        }
        response = self.session.get(f"{self._url}/getFloorPrice/", params=params)
        data = response.json()

        opensea_error = data["openSea"].get("error", None)
        looksrare_error = data["looksRare"].get("error", None)

        if opensea_error and looksrare_error:
            raise AlchemyFloorPriceError

        return data

    def create_webhook_address(
        self, wallet_address, webhook_id=settings.ALCHEMY_WEBHOOK_WALLET_ACTIVITY_ID
    ):
        payload = {
            "webhook_id": webhook_id,
            "addresses_to_add": [wallet_address],
            "addresses_to_remove": [],
        }
        headers = {
            "X-Alchemy-Token": self.auth_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        response = requests.patch(
            f"{self._dashboard_url}/update-webhook-addresses",
            json=payload,
            headers=headers,
        )
        return response

    def create_notify_webhook(self, webhook_url, wallet_addresses=None):
        url = f"{self._dashboard_url}/create-webhook"

        payload = {
            "addresses": wallet_addresses,
            "network": "ETH_MAINNET",
            "webhook_type": "ADDRESS_ACTIVITY",
            "webhook_url": webhook_url,
        }
        headers = {
            "Accept": "application/json",
            "X-Alchemy-Token": settings.ALCHEMY_AUTH_TOKEN,
            "Content-Type": "application/json",
        }

        response = requests.post(url, json=payload, headers=headers)
        return response

    def get_ryft_collection_owners(self):
        params = {
            "contractAddress": settings.RYFT_CONTRACT_ADDRESS,
            "withTokenBalances": False,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        response = self.session.get(
            f"{self._url}/getOwnersForCollection", headers=headers, params=params
        )
        data = response.json()
        return data

    def get_collection_transactions(self, contract_addresses, last_block=0, page=None):
        url = f"https://eth-mainnet.alchemyapi.io/v2/{self.api_key}"

        params = {
            "fromBlock": hex(int(last_block)),
            "toBlock": "latest",
            "category": ["erc721", "erc1155"],
            "withMetadata": True,
            "contractAddresses": contract_addresses,
            "maxCount": "0x3e8",  # 1000 transactions
        }

        if page:
            params["pageKey"] = page

        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getAssetTransfers",  # 150 CUPS
            "params": [params],
        }
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        response = self.alchemy_session.post(url, json=payload, headers=headers)
        return response.json()

    @retry(AlchemyRateLimitError, delay=2, tries=3, backoff=2)
    def get_wallet_transactions(
        self, wallet_address, last_block=0, transaction_type="receiver"
    ):
        url = f"https://eth-mainnet.alchemyapi.io/v2/{self.api_key}"

        params = {
            "fromBlock": hex(int(last_block)),
            "toBlock": "latest",
            "category": ["erc721", "erc1155"],
            "withMetadata": True,
            "maxCount": "0x3e8",  # 1000 transactions
        }

        if transaction_type == "receiver":
            params["toAddress"] = wallet_address
        else:
            params["fromAddress"] = wallet_address

        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "alchemy_getAssetTransfers",  # 150 CUPS
            "params": [params],
        }
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        response = self.alchemy_session.post(url, json=payload, headers=headers)

        if response.status_code == 429:
            raise AlchemyRateLimitError()

        data = response.json()

        error = data.get("error")
        if error:
            code = error.get("code")
            if code == 429:
                raise AlchemyRateLimitError()

        return data


alchemy_client = AlchemyClient()


def get_alchemy_client():
    return alchemy_client
