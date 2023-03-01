from unittest.mock import patch


class TestNFTPortClient:
    @patch("ryft.core.integrations.nftport.NFTPortClient")
    def test_get_contract_statistics(self, MockNFTPortClient):
        nftport_client = MockNFTPortClient()

        nftport_client.get_contract_statistics.return_value = {
            "response": "OK",
            "statistics": {
                "one_day_volume": 0.0,
                "one_day_change": -1.0,
                "one_day_sales": 0.0,
                "one_day_average_price": 0.0,
                "floor_price_historic_one_day": 0.085,
                "floor_price_historic_seven_day": 0.07,
                "floor_price_historic_thirty_day": 0.03,
            },
        }

        response = nftport_client.get_contract_statistics(contract_address="12345")

        assert response["response"] == "OK"

    @patch("ryft.core.integrations.nftport.NFTPortClient")
    def test_error_contract_statistics(self, MockNFTPortClient):
        nftport_client = MockNFTPortClient()

        nftport_client.get_contract_statistics.return_value = {
            "response": "NOK",
            "statistics": None,
        }

        response = nftport_client.get_contract_statistics(contract_address="12345")

        assert response["response"] == "NOK"


class TestAlchemyClient:
    @patch("ryft.core.integrations.alchemy.AlchemyClient")
    def test_get_nfts_for_wallet(self, MockAlchemyClient):
        alchemy_client = MockAlchemyClient()

        # TODO what is the test response?
        alchemy_client.get_nfts_for_wallet.return_value = {"response": "OK"}

        response = alchemy_client.get_nfts_for_wallet(wallet_address="12345")

        assert response["response"] == "OK"

    @patch("ryft.core.integrations.alchemy.AlchemyClient")
    def test_error_nfts_for_wallet(self, MockAlchemyClient):
        alchemy_client = MockAlchemyClient()

        alchemy_client.get_nfts_for_wallet.return_value = {"response": "NOK"}

        response = alchemy_client.get_nfts_for_wallet(wallet_address="12345")

        assert response["response"] == "NOK"
