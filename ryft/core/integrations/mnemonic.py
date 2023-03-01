import time

from django.conf import settings
from requests_ratelimiter import LimiterSession
from retry import retry


class TrendingBy:
    sales = "by_sales_count"
    volume = "by_sales_volume"
    price = "by_avg_price"


class MnemonicClient:
    """
    Client for implementing API calls to Mnemonic service
    """

    def __init__(self):
        self.api_key = settings.MNEMONIC_API_KEY
        self._url = "https://ethereum.rest.mnemonichq.com"
        self.session = LimiterSession(per_second=25)
        self.max_retries = 3

    @retry(ConnectionResetError, delay=10, tries=7)
    def get_wallet_nfts(self, wallet_address: str, limit: int = 500, offset: int = 0):
        url = f"{self._url}/tokens/v1beta1/by_owner/{wallet_address}"
        query = {
            "limit": str(limit),
            "offset": str(offset),
            "sortDirection": "SORT_DIRECTION_ASC",
        }
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        time.sleep(0.01)
        response = self.session.get(url, headers=headers, params=query)

        data = response.json()
        return data

    @retry(ConnectionResetError, delay=5, tries=3)
    def get_collection_transfers(
        self,
        contract_address: str,
        limit: int = 500,
        offset: int = 0,
        timestamp__gt=None,
    ):
        url = f"{self._url}/transfers/v1beta1/nft"

        if not timestamp__gt:
            timestamp__gt = "2022-07-24T01:00:22Z"

        query = {
            "limit": str(limit),
            "offset": str(offset),
            "sortDirection": "SORT_DIRECTION_ASC",
            "blockTimestampGt": timestamp__gt,
            "contractAddress": contract_address,
            "tokenTypes": ["TOKEN_TYPE_ERC721", "TOKEN_TYPE_ERC1155"],
        }

        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        time.sleep(0.01)
        response = self.session.get(url, headers=headers, params=query)

        data = response.json()
        return data

    @retry(ConnectionResetError, delay=5, tries=3)
    def get_historical_collection_owners(self, contract_address):
        params = {
            "duration": "DURATION_30_DAYS",
            "groupByPeriod": "GROUP_BY_PERIOD_1_DAY",
        }
        url = f"{self._url}/collections/v1beta1/owners_count/{contract_address}"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        time.sleep(0.01)
        response = self.session.get(url, params=params, headers=headers)
        data = response.json()
        return data

    @retry(ConnectionResetError, delay=5, tries=3)
    def get_historical_price_history(self, contract_address):
        params = {
            "duration": "DURATION_30_DAYS",
            "groupByPeriod": "GROUP_BY_PERIOD_1_DAY",
        }
        url = f"{self._url}/pricing/v1beta1/prices/by_contract/{contract_address}"
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        time.sleep(0.01)
        response = self.session.get(url, params=params, headers=headers)
        data = response.json()
        return data

    @retry(ConnectionResetError, delay=5, tries=3)
    def get_trending_collections(
        self, by: str = TrendingBy.sales, limit: int = 500, offset: int = 0
    ):
        url = f"{self._url}/collections/v1beta1/top/{by}"
        query = {
            "limit": str(limit),
            "offset": str(offset),
            "duration": "DURATION_1_DAY",
        }
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        time.sleep(0.01)
        response = self.session.get(url, headers=headers, params=query)
        data = response.json()
        return data

    @retry(ConnectionResetError, delay=5, tries=3)
    def get_ens_domains(self, wallet_address):
        url = f"{self._url}/ens/v1beta1/entity/by_address/{wallet_address}"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        time.sleep(0.01)
        response = self.session.get(url, headers=headers)
        data = response.json()
        return data

    @retry(ConnectionResetError, delay=5, tries=3)
    def get_collection_nfts(self, contract_address, limit: int, offset: int):
        url = f"{self._url}/tokens/v1beta1/by_contract/{contract_address}"

        query = {
            "limit": str(limit),
            "offset": str(offset),
            "sortDirection": "SORT_DIRECTION_ASC",
            "blockTimestampGt": "2019-08-24T14:15:22Z",
        }

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        time.sleep(0.01)
        response = self.session.get(url, headers=headers, params=query)
        data = response.json()
        return data

    @retry(ConnectionResetError, delay=5, tries=3)
    def get_token_metadata(self, contract_address: str, token_id: int):
        url = f"{self._url}/tokens/v1beta1/token/{contract_address}/{token_id}/metadata"

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        time.sleep(0.01)
        response = self.session.get(url, headers=headers)
        data = response.json()
        return data


mnemonic_client = MnemonicClient()
