from django.conf import settings
from requests_ratelimiter import LimiterSession

from .errors import (
    NFTPortContractNotFound,
    NFTPortContractStatisticsError,
    NFTPortPageEnumerationError,
    NFTPortRateLimitError,
    NFTPortServerError,
    NFTPortWalletNFTsError,
    NFTPortWalletTransactionsError,
)


class NFTPortClient:
    """
    Client for implementing API calls to NFTPort service
    """

    def __init__(self):
        self.api_key = settings.NFTPORT_API_KEY
        self._url = "https://api.nftport.xyz/v0"
        self.session = LimiterSession(per_second=3)

    def get_wallet_nfts(self, wallet_address: str, continuation: str = None):
        params = {
            "chain": "ethereum",
            "continuation": continuation,
            "page_size": 50,
            "include": ["metadata", "contract_information"],
        }
        headers = {"Content-Type": "application/json", "Authorization": self.api_key}
        response = self.session.get(
            f"{self._url}/accounts/{wallet_address}",
            params=params,
            headers=headers,
        )
        data = response.json()

        if data.get("error", None):
            status = data["error"]["status_code"]
            message = data["error"]["message"]

            if status == 429:
                raise NFTPortRateLimitError(f"Error code: {status}. Message: {message}")

            raise NFTPortWalletNFTsError(f"Error code: {status}. Message: {message}")

        return data

    def get_contract_statistics(self, contract_address):
        params = {"chain": "ethereum"}
        headers = {"Content-Type": "application/json", "Authorization": self.api_key}
        response = self.session.get(
            f"{self._url}/transactions/stats/{contract_address}",
            params=params,
            headers=headers,
        )
        data = response.json()

        if data.get("error", None):
            status = data["error"].get("status_code")
            message = data["error"].get("message")

            if status == 429:
                raise NFTPortRateLimitError(f"Error code: {status}. Message: {message}")

            if status == 404:
                raise NFTPortContractNotFound(message)

            raise NFTPortContractStatisticsError(
                f"Error code: {status}. Message: {message}"
            )

        return data

    def get_wallet_transactions(
        self, wallet_address: str, t_type: str, continuation: str = None
    ):
        params = {
            "chain": "ethereum",
            "continuation": continuation,
            "page_size": 50,
            "type": t_type,  # transfer_from transfer_to mint burn buy sell all
        }
        headers = {"Content-Type": "application/json", "Authorization": self.api_key}
        response = self.session.get(
            f"{self._url}/transactions/accounts/{wallet_address}",
            params=params,
            headers=headers,
        )
        data = response.json()

        if data.get("error", None):
            status = data["error"]["status_code"]
            message = data["error"]["message"]

            if status == 429:
                raise NFTPortRateLimitError(f"Error code: {status}. Message: {message}")

            raise NFTPortWalletTransactionsError(
                f"Error code: {status}. Message: {message}"
            )

        return data

    def get_contract_nfts(self, contract_address: str, page: int = 1):
        params = {
            "chain": "ethereum",
            "page_number": page,
            "page_size": 50,
            "include": ["metadata"],
        }
        headers = {"Content-Type": "application/json", "Authorization": self.api_key}
        response = self.session.get(
            f"{self._url}/nfts/{contract_address}",
            params=params,
            headers=headers,
        )

        data = response.json()

        if data.get("error", None):
            status = data["error"]["status_code"]
            message = data["error"]["message"]

            if status == 429:
                raise NFTPortRateLimitError(f"Error code: {status}. Message: {message}")

            elif status == 422:
                raise NFTPortPageEnumerationError(
                    f"Error code: {status}. Message: {message}"
                )

            elif status == 500:
                raise NFTPortServerError(f"Error code: {status}. Message: {message}")

            raise NFTPortWalletNFTsError(f"Error code: {status}. Message: {message}")

        return data


nftport_client = NFTPortClient()
