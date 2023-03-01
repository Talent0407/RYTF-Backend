import datetime
import json
import logging
from decimal import Decimal
from itertools import chain

from dateutil import parser
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from config.settings.base import RYFT_CONTRACT_ADDRESS
from ryft.core.api.filters import (
    CollectionFilter,
    CollectionTransfersFilter,
    TrackedWalletFilter,
)
from ryft.core.api.paginators import (
    CollectionResultsSetPagination,
    CollectionTransferResultsSetPagination,
    NFTResultsSetPagination,
    TransactionResultsSetPagination,
)
from ryft.core.api.permissions import IsMember, IsValidDiscordUser, IsWalletOwner
from ryft.core.api.serializers import (
    CollectionCreateSerializer,
    CollectionDetailSerializer,
    CollectionListSerializer,
    CollectionTransferSerializer,
    CollectionVoteSerializer,
    ExtendedNFTSerializer,
    NFTSerializer,
    ProfilePictureSerializer,
    ProfileSerializer,
    TrackedWalletSerializer,
    TransactionSerializer,
    UpcomingCollectionSerializer,
    UserTrackedWalletCreateSerializer,
    UserTrackedWalletSerializer,
    UserWhiteListCreateSerializer,
    UserWhiteListSerializer,
    WalletNFTSerializer,
    WalletPortfolioRecordSerializer,
)
from ryft.core.authentication import CsrfExemptSessionAuthentication
from ryft.core.models import (
    NFT,
    Collection,
    CollectionVote,
    EthPrice,
    TrackedWallet,
    Transaction,
    TrendingCollections,
    UserTrackedWallet,
    UserWhiteList,
    Wallet,
    WalletNFT,
)
from ryft.core.portfolio.tasks import run_new_wallet_tasks
from ryft.core.utils import (
    DISCORD_API_ENDPOINT,
    discord_request,
    get_user_discord_roles,
    is_valid_signature_for_string_body,
)

User = get_user_model()


class UserProfileView(RetrieveAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    queryset = Wallet.objects.all()

    def get_object(self):
        obj = self.request.user.wallet
        return obj


class UserProfileViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, IsMember]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    queryset = Wallet.objects.none()
    lookup_field = "ethereum_address"

    def get_object(self):
        return self.request.user.wallet

    def get_queryset(self, *args, **kwargs):
        return self.queryset.filter(wallet=self.request.user.wallet)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class UserProfilePictureViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = ProfilePictureSerializer
    permission_classes = [IsAuthenticated, IsMember]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (MultiPartParser, FormParser)
    queryset = Wallet.objects.none()
    lookup_field = "ethereum_address"

    def get_object(self):
        return self.request.user.wallet

    def get_queryset(self, *args, **kwargs):
        return self.queryset.filter(wallet=self.request.user.wallet)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class CollectionViewSet(
    ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet
):
    permission_classes = [IsAuthenticated, IsMember]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    pagination_class = CollectionResultsSetPagination
    queryset = (
        Collection.objects.select_related("collectionmetrics")
        .prefetch_related("artwork_images")
        .order_by(F("collectionmetrics__current_floor_price").desc(nulls_last=True))
        .distinct()
    )

    filterset_class = CollectionFilter
    search_fields = ["name"]
    lookup_field = "contract_address"

    def filter_queryset(self, queryset):
        filter_backends = [DjangoFilterBackend, filters.SearchFilter]

        for backend in list(filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, view=self)
        return queryset

    def perform_create(self, serializer):
        serializer.save(community_submitted=True)

    def get_serializer_class(self):
        if self.action == "list":
            return CollectionListSerializer
        elif self.action == "retrieve":
            return CollectionDetailSerializer
        return CollectionCreateSerializer

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=False)
    def upcoming(self, request):
        upcoming_queryset_base = (
            Collection.objects.select_related("collectionmetrics")
            .prefetch_related("artwork_images")
            .filter(released=False, verified=True)
        )

        # fetch collections that will be releasing after datetime.now()
        upcoming_queryset_gte = upcoming_queryset_base.filter(
            mint_date__gte=datetime.datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
        ).order_by("mint_date")

        # fetch collections with null mint_date
        upcoming_queryset_isnull = upcoming_queryset_base.filter(mint_date__isnull=True)

        # merge the two query sets
        upcoming_queryset = list(chain(upcoming_queryset_gte, upcoming_queryset_isnull))

        serializer = UpcomingCollectionSerializer(
            upcoming_queryset, context={"request": request}, many=True
        )
        return Response(status=status.HTTP_200_OK, data=serializer.data)

    @action(detail=True)
    def votes(self, request, contract_address):
        collection = Collection.objects.get(contract_address=contract_address)
        collection_votes = CollectionVote.objects.filter(collection=collection)
        up_votes = collection_votes.filter(vote_type="Up").count()
        down_votes = collection_votes.filter(vote_type="Down").count()
        return Response({"up_votes": up_votes, "down_votes": down_votes})


class CollectionVoteView(APIView):
    permission_classes = [IsAuthenticated, IsMember]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    serializer_class = CollectionVoteSerializer

    def get(self, request, *args, **kwargs):
        contract_address = self.kwargs.get("contract_address")
        collection = Collection.objects.get(contract_address=contract_address)
        try:
            vote = CollectionVote.objects.get(collection=collection, user=request.user)
            data = {"vote_exists": True}
            data.update(self.serializer_class(vote).data)
            return Response(data)
        except CollectionVote.DoesNotExist:
            data = {"vote_exists": False}
            return Response(data)

    def post(self, request, *args, **kwargs):
        contract_address = self.kwargs.get("contract_address")
        serializer = CollectionVoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vote_type = serializer.data.get("vote_type")
        collection = Collection.objects.get(contract_address=contract_address)

        user_votes = CollectionVote.objects.filter(
            user=request.user, collection=collection
        )
        if user_votes.exists():
            vote = user_votes.get()

            if vote_type == vote.vote_type:
                vote.delete()
            else:
                vote.vote_type = vote_type
                vote.save()
        else:
            CollectionVote.objects.create(
                collection=collection, user=request.user, vote_type=vote_type
            )
        return Response({"vote_type": vote_type}, status=200)


class CollectionTransfersAPIView(ListAPIView):
    permission_classes = [IsAuthenticated, IsMember]
    serializer_class = CollectionTransferSerializer
    pagination_class = CollectionTransferResultsSetPagination

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        contract_address = self.kwargs.get("contract_address")
        get_object_or_404(Collection, contract_address=contract_address)
        return (
            Transaction.objects.select_related("nft")
            .filter(
                contract_address=contract_address, collection_only=True, price_eth__gt=0
            )
            .order_by("-transaction_date")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class CollectionTransfersGraphView(ListAPIView):
    permission_classes = [IsAuthenticated, IsMember]
    filterset_class = CollectionTransfersFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.values(
            "id",
            "transaction_date",
            "price_eth",
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = list(page)
            return self.get_paginated_response(data)

        data = list(queryset)
        return Response(data)

    def get_queryset(self):
        contract_address = self.kwargs.get("contract_address")
        get_object_or_404(Collection, contract_address=contract_address)
        thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
        return (
            Transaction.objects.select_related("nft")
            .filter(
                contract_address=contract_address,
                collection_only=True,
                price_eth__gt=0,
                transaction_date__gte=thirty_days_ago,
            )
            .order_by("-transaction_date")
        )


class WalletViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsMember]
    serializer_class = TrackedWalletSerializer
    queryset = TrackedWallet.objects.select_related("wallet").all()
    lookup_field = "wallet__wallet_address"
    filterset_class = TrackedWalletFilter
    pagination_class = CollectionTransferResultsSetPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        tracked_wallets = UserTrackedWallet.objects.select_related(
            "tracked_wallet"
        ).filter(user=user)
        tracked_wallet_ids = tracked_wallets.values_list(
            "tracked_wallet__id", flat=True
        )
        context.update({"tracked_wallet_ids": tracked_wallet_ids, "user": user})
        return context


class WalletPortfolioView(ListAPIView):
    permission_classes = [IsAuthenticated, IsMember]
    serializer_class = WalletPortfolioRecordSerializer

    def get_queryset(self):
        user: User = self.request.user
        wallet = user.wallet

        wallet_address = self.request.GET.get("wallet_address")
        if wallet_address:
            tracked_wallet = get_object_or_404(
                TrackedWallet, wallet__wallet_address=wallet_address.lower()
            )
            wallet = tracked_wallet.wallet

        return wallet.wallet_portfolios.all().order_by("-id")[:30]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class WalletNFTAPIView(ListAPIView):
    permission_classes = [IsAuthenticated, IsMember]
    serializer_class = WalletNFTSerializer
    pagination_class = NFTResultsSetPagination

    def get_queryset(self):
        # This API endpoint is also used to fetch NFTs for tracked wallets
        user: User = self.request.user
        wallet = user.wallet

        # Check for request param
        contract_address = self.request.GET.get("contract_address")
        wallet_address = self.request.GET.get("wallet_address")

        if wallet_address:
            tracked_wallet = get_object_or_404(
                TrackedWallet, wallet__wallet_address=wallet_address.lower()
            )
            wallet = tracked_wallet.wallet

        qs = WalletNFT.objects.select_related(
            "nft", "nft__collection", "nft__collection__collectionmetrics"
        ).filter(wallet=wallet)

        if contract_address:
            qs = qs.filter(
                Q(nft__collection__contract_address=contract_address)
                | Q(nft_raw_data__contract_address=contract_address)
            ).distinct()

        # ordering
        ordering = self.request.GET.get("order_by")

        if not ordering:
            qs = qs.order_by(F("nft").desc(nulls_last=True))

        elif ordering == "rarity":
            qs = qs.order_by(F("nft__rarity_score").desc(nulls_last=True))

        elif ordering == "floor_price_hl":
            qs = qs.order_by(
                F("nft__collection__collectionmetrics__current_floor_price").desc(
                    nulls_last=True
                )
            )

        elif ordering == "floor_price_lh":
            qs = qs.order_by(
                F("nft__collection__collectionmetrics__current_floor_price")
            )

        elif ordering == "az":
            qs = qs.order_by(F("nft__collection__name").asc())

        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class WalletTransactionsAPIView(ListAPIView):
    permission_classes = [IsAuthenticated, IsMember]
    serializer_class = TransactionSerializer
    pagination_class = TransactionResultsSetPagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.values(
            "id",
            "transaction_type",
            "transfer_from",
            "transfer_to",
            "contract_address",
            "quantity",
            "transaction_hash",
            "block_hash",
            "block_number",
            "transaction_date",
            "price_eth",
            "price_usd",
        ).annotate(
            nft_id=F("nft__id"),
            name=F("nft__name"),
            collection_name=F("nft__collection__name"),
            token_id=F("nft__token_id"),
            image_url=F("nft__image_url"),
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = list(page)
            return self.get_paginated_response(data)

        data = list(queryset)
        return Response(data)

    def get_queryset(self):
        user: User = self.request.user
        wallet = user.wallet

        # Check for request param
        wallet_address = self.request.GET.get("wallet_address")
        if wallet_address:
            tracked_wallet = get_object_or_404(
                TrackedWallet, wallet__wallet_address=wallet_address.lower()
            )
            wallet = tracked_wallet.wallet

        return (
            Transaction.objects.filter(wallet=wallet)
            .select_related("nft", "nft__collection")
            .order_by("-transaction_date")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class NFTListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated, IsMember]
    serializer_class = NFTSerializer
    pagination_class = NFTResultsSetPagination

    @method_decorator(cache_page(60 * 60 * 2))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        contract_address = self.kwargs.get("contract_address")
        collection = get_object_or_404(Collection, contract_address=contract_address)
        return collection.nfts.all().order_by("rank")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class NFTViewSet(RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsMember]
    serializer_class = ExtendedNFTSerializer
    queryset = NFT.objects.select_related("collection").all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["collection", "rarity_score", "rank"]


class UserWhitelistViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    CreateModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsWalletOwner, IsMember]
    queryset = UserWhiteList.objects.none()
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_serializer_class(self, *args, **kwargs):
        if self.request.method == "POST":
            return UserWhiteListCreateSerializer
        return UserWhiteListSerializer

    def get_queryset(self):
        user_whitelist_base = UserWhiteList.objects.select_related("collection").filter(
            user=self.request.user, collection__released=False
        )

        # fetch collections that will be releasing after datetime.now()
        user_whitelist_gtw = user_whitelist_base.filter(
            collection__mint_date__gte=datetime.datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
        ).order_by("collection__mint_date")

        # fetch collections with null mint_date
        user_whitelist_isnull = user_whitelist_base.filter(
            collection__mint_date__isnull=True
        )

        return list(chain(user_whitelist_gtw, user_whitelist_isnull))

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            whitelist = UserWhiteList.objects.get(
                collection=request.data["collection"], user=request.user
            )
            serializer = self.get_serializer(whitelist)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserWhiteList.DoesNotExist:
            return super().create(request, *args, **kwargs)


class UserTrackedWalletViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    DestroyModelMixin,
    GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsMember]
    queryset = UserTrackedWallet.objects.none()
    authentication_classes = (CsrfExemptSessionAuthentication,)

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.values("id", "name").annotate(
            thumbnail=F("tracked_wallet__thumbnail"),
            wallet_address=F("tracked_wallet__wallet__wallet_address"),
            ens_domain=F("tracked_wallet__wallet__ens_domain"),
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            data = list(page)
            return self.get_paginated_response(data)

        data = list(queryset)
        return Response(data)

    def get_queryset(self):
        return UserTrackedWallet.objects.select_related(
            "tracked_wallet", "tracked_wallet__wallet"
        ).filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserTrackedWalletCreateSerializer
        return UserTrackedWalletSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet_address = serializer.data.get("wallet_address").lower()
        name = serializer.data.get("name")

        # 1. check if address is already being tracked
        wallet, created_wallet = Wallet.objects.get_or_create(
            wallet_address=wallet_address
        )

        user_owned_addresses = [request.user.wallet.wallet_address]

        if wallet_address in user_owned_addresses:
            return Response(
                {"message": "You cannot add your own wallet as a tracked wallet"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tracked_wallet, created = TrackedWallet.objects.get_or_create(wallet=wallet)

        if created_wallet:
            # 2. Fetch data and create webhook for new wallet
            transaction.on_commit(
                lambda: run_new_wallet_tasks(wallet.wallet_address, tracked_wallet=True)
            )

        try:
            UserTrackedWallet.objects.get(
                tracked_wallet=tracked_wallet, user=request.user
            )
            return Response(
                {"message": "You are already tracking this wallet"},
                status=status.HTTP_200_OK,
            )
        except UserTrackedWallet.DoesNotExist:
            utw = UserTrackedWallet.objects.create(
                tracked_wallet=tracked_wallet, user=request.user
            )
            utw.name = name
            utw.save()

        return Response(serializer.data, status=status.HTTP_200_OK)


class TrendingCollectionsView(APIView):
    permission_classes = [IsAuthenticated, IsMember]

    def get(self, request, *args, **kwargs):
        trending_collections = TrendingCollections.objects.order_by(
            "-timestamp"
        ).first()

        data = {
            "trending_by_volume": trending_collections.trending_by_volume,
            "trending_by_sales": trending_collections.trending_by_sales,
            "trending_by_price": trending_collections.trending_by_price,
        }
        return Response(data, status=status.HTTP_200_OK)


@csrf_exempt
def wallet_activity_webhook(request):
    payload = request.body
    sig_header = request.META["HTTP_X_ALCHEMY_SIGNATURE"]
    signing_key = settings.ALCHEMY_WEBHOOK_KEY

    if not is_valid_signature_for_string_body(payload, sig_header, signing_key):
        logging.error(
            msg="Unsuccessful Alchemy wallet activity webhook. An Invalid signature occurred",
        )
        return HttpResponse(status=400)

    logging.info(msg="Received wallet address activity")

    data = json.loads(payload)

    event = data["event"]
    activity = event["activity"]
    logging.info(msg=f"Here is the activity in the event: {activity}")

    null_address = "0x0000000000000000000000000000000000000000"

    def get_transaction_type(t):
        transaction_type = "transfer"
        from_address = t.get("from")
        to_address = t.get("to")

        if from_address == null_address:
            transaction_type = "mint"

        elif to_address == null_address:
            transaction_type = "burn"

        return transaction_type

    for t in activity:

        category = t.get("category")
        if category != "token":
            transaction_date = parser.parse(data.get("createdAt")).date()

            from_address = t.get("fromAddress")
            to_address = t.get("toAddress")

            raw_contract = t.get("rawContract")
            contract_address = raw_contract.get("address")

            is_ryft_transfer = False
            if contract_address == RYFT_CONTRACT_ADDRESS:
                is_ryft_transfer = True

            price_eth = None
            price_usd = None

            erc1155_metadata = t.get("erc1155Metadata")
            erc721_token_id = t.get("erc721TokenId")

            token_id = None

            if erc1155_metadata:
                if len(erc1155_metadata) > 0:
                    token_id = int(erc1155_metadata[0].get("tokenId"), base=16)
                    price_eth_hex = erc1155_metadata[0].get("value")
                    price_eth = int(price_eth_hex, base=16)
            elif erc721_token_id:
                token_id = int(erc721_token_id, base=16)

            if token_id:

                value = t.get("value")
                if value:
                    price_eth = value

                if price_eth:
                    ether_price = (
                        EthPrice.objects.filter(date__lte=transaction_date)
                        .order_by("-date")
                        .first()
                    )
                    if ether_price:
                        price_usd = int(
                            Decimal(ether_price.value) * Decimal(str(price_eth))
                        )

                nft = NFT.objects.filter(
                    collection__contract_address=contract_address, token_id=token_id
                ).first()

                if from_address:
                    try:
                        wallet = Wallet.objects.get(wallet_address=from_address)
                        Transaction.objects.get_or_create(
                            wallet=wallet,
                            transaction_hash=t.get("transactionHash"),
                            defaults={
                                "nft": nft,
                                "transaction_type": get_transaction_type(t),
                                "transfer_from": from_address,
                                "transfer_to": to_address,
                                "contract_address": contract_address,
                                "token_id": token_id,
                                "quantity": 1,
                                "block_hash": t.get("blockHash"),
                                "block_number": t.get("blockNumber"),
                                "transaction_date": transaction_date,
                                "raw_transaction_data": t,
                                "price_eth": price_eth,
                                "price_usd": price_usd,
                            },
                        )
                        if is_ryft_transfer:
                            wallet.is_member = False
                            wallet.save()

                        if nft:
                            # delete the walletNFT because this is sent from the fromAddress
                            try:
                                wallet_nft = WalletNFT.objects.get(
                                    nft=nft, wallet=wallet
                                )
                                wallet_nft.delete()
                            except WalletNFT.DoesNotExist:
                                pass

                    except Wallet.DoesNotExist:
                        pass

                if to_address:
                    try:
                        wallet = Wallet.objects.get(wallet_address=to_address)
                        Transaction.objects.get_or_create(
                            wallet=wallet,
                            transaction_hash=t.get("transactionHash"),
                            defaults={
                                "nft": nft,
                                "transaction_type": get_transaction_type(t),
                                "transfer_from": from_address,
                                "transfer_to": to_address,
                                "contract_address": contract_address,
                                "token_id": token_id,
                                "quantity": 1,
                                "block_hash": t.get("blockHash"),
                                "block_number": t.get("blockNumber"),
                                "transaction_date": transaction_date,
                                "raw_transaction_data": t,
                                "price_eth": price_eth,
                                "price_usd": price_usd,
                            },
                        )
                        if is_ryft_transfer:
                            wallet.is_member = True
                            wallet.save()

                        if nft:
                            # create the walletNFT because this is sent to the toAddress
                            WalletNFT.objects.get_or_create(
                                nft=nft,
                                wallet=wallet,
                                defaults={
                                    "nft_raw_data": {
                                        "contract_address": contract_address,
                                        "token_id": token_id,
                                    }
                                },
                            )

                    except Wallet.DoesNotExist:
                        pass

    logging.info(msg="Finished wallet address webhook")
    return HttpResponse(status=200)


class IsBetaUserView(APIView):
    """given wallet address, gets the Discord user and checks whether
    the user is beta tester, by checking the user's discord roles
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        guild_user = get_user_discord_roles(request)
        if not guild_user:
            return Response(
                {"message": "Please connect your discord account to your wallet"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if "retry_after" in guild_user:
            return Response(
                {
                    "message": f"Rate limited by Discord, retry after {guild_user['retry_after']} seconds"
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        if "roles" not in guild_user:
            return Response(
                {"message": "Please join the RYFT Discord server"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(
            {
                "is_beta_tester": settings.RYFT_DISCORD_BETA_USER_ROLE_ID
                in guild_user["roles"]
            },
            status=status.HTTP_200_OK,
        )


class UserWhitelistView(APIView):
    """fetches user's discord roles and
    returns whitelisted collections based on roles
    """

    permission_classes = [IsValidDiscordUser]

    def get(self, request):
        guild_user = get_user_discord_roles(request)
        if not guild_user:
            return Response(
                {"message": "Please connect your discord account to your wallet"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if "refresh_token" in guild_user:
            return Response(
                {"message": "Please re-login using discord"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if "retry_after" in guild_user:
            return Response(
                {
                    "message": f"Rate limited by Discord, retry after {guild_user['retry_after']} seconds"
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        if "roles" not in guild_user:
            return Response(
                {"message": "Please join the RYFT Discord server"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if settings.RYFT_DISCORD_BETA_USER_ROLE_ID not in guild_user["roles"]:
            return Response(
                {"message": "Unauthorised"}, status=status.HTTP_401_UNAUTHORIZED
            )

        user_role_names = []

        ryft_guild_id = settings.RYFT_DISCORD_SERVER_ID

        # fetch guild roles
        guild_roles = discord_request(
            "GET",
            f"{DISCORD_API_ENDPOINT}/guilds/{ryft_guild_id}/roles",
            {},
            {"Authorization": "Bot %s" % settings.DISCORD_BOT_TOKEN},
            None,
        )

        if "retry_after" in guild_roles:
            return Response(
                {
                    "message": f"Rate limited by Discord, retry after {guild_roles['retry_after']} seconds"
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        for guild_role in guild_roles:
            if guild_role["id"] in guild_user["roles"]:
                user_role_names.append(guild_role["name"])

        # fetch collections that will be releasing after datetime.now()
        collection_queryset_gte = Collection.objects.filter(
            name__in=user_role_names,
            mint_date__gte=datetime.datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
        ).order_by("mint_date")

        # fetch collections with null mint_date
        collection_queryset_isnull = Collection.objects.filter(
            name__in=user_role_names, mint_date__isnull=True
        )

        # merge the two query sets
        collection_queryset = list(
            chain(collection_queryset_gte, collection_queryset_isnull)
        )

        serializer = UpcomingCollectionSerializer(
            collection_queryset, context={"request": request}, many=True
        )

        return Response(
            {"collections": serializer.data},
            status=status.HTTP_200_OK,
        )
