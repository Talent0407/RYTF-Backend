import pytest
from rest_framework.test import APIClient

from ryft.core.tests.factories import (
    CollectionFactory,
    NFTFactory,
    TransactionFactory,
    WalletFactory,
    WalletNFTFactory,
    WalletPortfolioRecordFactory,
)
from ryft.users.models import User
from ryft.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture(scope="session")
def celery_config():
    return {"broker_url": "memory://", "result_backend": "redis://"}


@pytest.fixture
def user() -> User:
    return UserFactory()


@pytest.fixture
def api_client():
    return APIClient


@pytest.fixture
def collection():
    return CollectionFactory()


@pytest.fixture
def wallet():
    return WalletFactory()


@pytest.fixture
def wallet_portfolio_record():
    return WalletPortfolioRecordFactory()


@pytest.fixture
def wallet_nft():
    return WalletNFTFactory()


@pytest.fixture
def nft():
    return NFTFactory()


@pytest.fixture
def transaction():
    return TransactionFactory()
