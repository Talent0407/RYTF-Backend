from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter, SimpleRouter

from ryft.core.api.views import (
    CollectionTransfersAPIView,
    CollectionTransfersGraphView,
    CollectionViewSet,
    CollectionVoteView,
    NFTListAPIView,
    NFTViewSet,
    TrendingCollectionsView,
    UserProfilePictureViewSet,
    UserProfileView,
    UserProfileViewSet,
    UserTrackedWalletViewSet,
    UserWhitelistViewSet,
    WalletNFTAPIView,
    WalletPortfolioView,
    WalletTransactionsAPIView,
    WalletViewSet,
)

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

# router.register("users", UserViewSet)
router.register("collections", CollectionViewSet)
router.register("wallets", WalletViewSet)
router.register("nfts", NFTViewSet)
router.register("whitelists", UserWhitelistViewSet)
router.register("tracked-wallets", UserTrackedWalletViewSet)
router.register("me", UserProfileViewSet)
router.register("avatar", UserProfilePictureViewSet)

app_name = "api"
urlpatterns = router.urls
urlpatterns += [
    path("me/", UserProfileView.as_view()),
    path(
        "collections/<contract_address>/transfers/",
        CollectionTransfersAPIView.as_view(),
    ),
    path(
        "collections/<contract_address>/transfers/graph/",
        CollectionTransfersGraphView.as_view(),
    ),
    path("wallet/portfolio/", WalletPortfolioView.as_view()),
    path("wallet/transactions/", WalletTransactionsAPIView.as_view()),
    path("wallet/nfts/", WalletNFTAPIView.as_view()),
    path("collections/<contract_address>/nfts/", NFTListAPIView.as_view()),
    path("trending-collections/", TrendingCollectionsView.as_view()),
    path("collections/<contract_address>/user-vote/", CollectionVoteView.as_view()),
]
