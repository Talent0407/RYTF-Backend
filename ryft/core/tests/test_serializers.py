import factory
import pytest

from ryft.core.api.serializers import (
    CollectionSerializer,
    TransactionSerializer,
    WalletCreateSerializer,
    WalletNFTSerializer,
    WalletPortfolioRecordSerializer,
    WalletSerializer,
)
from ryft.core.tests.factories import (
    CollectionFactory,
    TransactionFactory,
    WalletFactory,
    WalletNFTFactory,
    WalletPortfolioRecordFactory,
)


class TestCollectionSerializer:
    def test_serialize_model(self):
        collection = CollectionFactory.build()
        serializer = CollectionSerializer(collection)

        assert serializer.data

    def test_serialized_data(self):
        valid_serialized_data = factory.build(dict, FACTORY_CLASS=CollectionFactory)

        serializer = CollectionSerializer(data=valid_serialized_data)

        assert serializer.is_valid()
        assert serializer.errors == {}


class TestWalletSerializer:
    def test_serialize_model(self):
        wallet = WalletFactory.build()
        serializer = WalletSerializer(wallet)

        assert serializer.data

    def test_serialized_data(self):
        valid_serialized_data = factory.build(dict, FACTORY_CLASS=WalletFactory)

        serializer = WalletSerializer(data=valid_serialized_data)

        assert serializer.is_valid()
        assert serializer.errors == {}


class TestWalletCreateSerializer:
    def test_serialize_model(self):
        wallet = WalletFactory.build()
        serializer = WalletCreateSerializer(wallet)

        assert serializer.data

    @pytest.mark.django_db
    def test_serialized_data(self):
        valid_serialized_data = factory.build(dict, FACTORY_CLASS=WalletFactory)

        serializer = WalletCreateSerializer(data=valid_serialized_data)

        assert serializer.is_valid()
        assert serializer.errors == {}


class TestWalletPortfolioRecordSerializer:
    def test_serialize_model(self):
        collection = WalletPortfolioRecordFactory.build()
        serializer = WalletPortfolioRecordSerializer(collection)

        assert serializer.data

    def test_serialized_data(self):
        valid_serialized_data = factory.build(
            dict, FACTORY_CLASS=WalletPortfolioRecordFactory
        )

        serializer = WalletPortfolioRecordSerializer(data=valid_serialized_data)

        assert serializer.is_valid()
        assert serializer.errors == {}


class TestWalletNFTSerializer:
    def test_serialize_model(self):
        collection = WalletNFTFactory.build()
        serializer = WalletNFTSerializer(collection)

        assert serializer.data

    def test_serialized_data(self):
        valid_serialized_data = factory.build(dict, FACTORY_CLASS=WalletNFTFactory)

        serializer = WalletNFTSerializer(data=valid_serialized_data)

        assert serializer.is_valid()
        assert serializer.errors == {}


class TestTransactionSerializer:
    def test_serialize_model(self):
        collection = TransactionFactory.build()
        serializer = TransactionSerializer(collection)

        assert serializer.data

    def test_serialized_data(self):
        valid_serialized_data = factory.build(dict, FACTORY_CLASS=TransactionFactory)

        serializer = TransactionSerializer(data=valid_serialized_data)

        assert serializer.is_valid()
        assert serializer.errors == {}
