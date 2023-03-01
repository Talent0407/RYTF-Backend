from rest_framework import serializers
from web3 import Web3

from ryft.core.models import (
    NFT,
    ArtworkPreviewImage,
    Collection,
    CollectionMetrics,
    CollectionVote,
    DiscordUser,
    TrackedWallet,
    Transaction,
    UserTrackedWallet,
    UserWhiteList,
    Wallet,
    WalletNFT,
    WalletPortfolioRecord,
)


class ArtworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtworkPreviewImage
        fields = ("image",)
        read_only_fields = ("image",)


class CollectionVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionVote
        fields = ("vote_type",)


class CollectionMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionMetrics
        fields = (
            "current_floor_price",
            "average_price_24hr",
            "average_sales_24hr",
            "average_volume_24hr",
            "royalty_fee",
            "price_history",
            "owners_history",
        )


class CollectionListSerializer(serializers.ModelSerializer):
    collectionmetrics = CollectionMetricsSerializer()

    class Meta:
        model = Collection
        fields = (
            "id",
            "name",
            "contract_address",
            "thumbnail",
            "collectionmetrics",
            "verified",
            "released",
            "discord_link",
            "twitter_link",
            "website_link",
            "opensea_link",
            "num_discord_members",
            "num_twitter_followers",
            "created_timestamp",
        )
        read_only_fields = (
            "id",
            "name",
            "contract_address",
            "thumbnail",
            "collectionmetrics",
            "verified",
            "released",
            "discord_link",
            "twitter_link",
            "website_link",
            "opensea_link",
            "num_discord_members",
            "num_twitter_followers",
            "created_timestamp",
        )


def required(value):
    if value is None:
        raise serializers.ValidationError("This field is required")


def valid_discord_link(value):
    if value:
        if "https://discord.gg" not in value:
            raise serializers.ValidationError(
                "Discord link is not valid. Please include 'https://discord.gg' in your link"
            )


def valid_twitter_link(value):
    if value:
        if "https://twitter.com" not in value:
            raise serializers.ValidationError(
                "Discord link is not valid. Please include 'https://twitter.com' in your link"
            )


def valid_opensea_link(value):
    if value:
        if "https://opensea.io" not in value:
            raise serializers.ValidationError(
                "Opensea link is not valid. Please include 'https://opensea.io' in your link"
            )


def valid_contract_address(value):
    if not Web3.isAddress(value):
        raise serializers.ValidationError("Invalid address")

    qs = Collection.objects.filter(contract_address=str(value).lower())
    if qs.exists():
        raise serializers.ValidationError(
            "This contract has already been added to our database"
        )


class CollectionCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(validators=[required])
    description = serializers.CharField(validators=[required])
    contract_address = serializers.CharField(
        validators=[required, valid_contract_address]
    )
    supply = serializers.IntegerField(validators=[required])
    thumbnail = serializers.ImageField(required=False)
    discord_link = serializers.CharField(
        required=False, validators=[valid_discord_link]
    )
    twitter_link = serializers.CharField(
        required=False, validators=[valid_twitter_link]
    )
    website_link = serializers.CharField(required=False)
    opensea_link = serializers.CharField(
        required=False, validators=[valid_opensea_link]
    )

    class Meta:
        model = Collection
        fields = (
            "name",
            "description",
            "contract_address",
            "supply",
            "thumbnail",
            "discord_link",
            "twitter_link",
            "website_link",
            "opensea_link",
            "num_discord_members",
            "num_twitter_followers",
        )


class UpcomingCollectionSerializer(serializers.ModelSerializer):
    artwork_images = ArtworkSerializer(many=True, read_only=True)
    collectionmetrics = CollectionMetricsSerializer(read_only=True)

    class Meta:
        model = Collection
        exclude = ("contract_abi",)
        read_only_fields = (
            "id",
            "name",
            "description",
            "contract_address",
            "supply",
            "mint_date",
            "mint_price",
            "released",
            "verified",
            "discord_link",
            "twitter_link",
            "website_link",
            "opensea_link",
            "artwork_images",
            "num_discord_members",
            "num_twitter_followers",
            "thumbnail",
            "collectionmetrics",
        )


class CollectionDetailSerializer(serializers.ModelSerializer):
    artwork_images = ArtworkSerializer(many=True, read_only=True)
    collectionmetrics = CollectionMetricsSerializer(read_only=True)

    class Meta:
        model = Collection
        exclude = ("contract_abi",)
        read_only_fields = (
            "id",
            "name",
            "description",
            "contract_address",
            "supply",
            "mint_date",
            "mint_price",
            "released",
            "verified",
            "discord_link",
            "twitter_link",
            "website_link",
            "opensea_link",
            "artwork_images",
            "num_discord_members",
            "num_twitter_followers",
            "thumbnail",
            "collectionmetrics",
            "created_timestamp",
        )


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("wallet_address",)
        read_only_fields = ("wallet_address",)


class WalletCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("wallet_address",)
        read_only_fields = ()


class WalletPortfolioRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletPortfolioRecord
        fields = ("portfolio_value", "timestamp")
        read_only_fields = ("portfolio_value", "timestamp")


class ProfileSerializer(serializers.ModelSerializer):
    discord_user = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = (
            "display_name",
            "custom_thumbnail",
            "thumbnail",
            "ens_domain",
            "wallet_address",
            "discord_user",
        )
        read_only_fields = (
            "ens_domain",
            "custom_thumbnail",
            "thumbnail",
            "wallet_address",
        )

    def get_discord_user(self, obj: Wallet):
        try:
            discord_user = DiscordUser.objects.get(user=obj.user)
            if not discord_user.refresh_token:
                return None
            return {
                "id": str(discord_user.id),  # careful of overflow of integers,
                "username": discord_user.discord_tag,
                "avatar": discord_user.avatar,
            }
        except DiscordUser.DoesNotExist:
            return None


class ProfilePictureSerializer(serializers.ModelSerializer):
    custom_thumbnail = serializers.ImageField()

    class Meta:
        model = Wallet
        fields = ("custom_thumbnail",)


class NFTSerializer(serializers.ModelSerializer):
    contract_address = serializers.SerializerMethodField()

    class Meta:
        model = NFT
        fields = (
            "id",
            "name",
            "contract_address",
            "token_id",
            "image_url",
            "rarity_score",
            "rank",
            "buy_rank",
            "raw_metadata",
            "trait_count",
        )
        read_only_fields = (
            "id",
            "name",
            "contract_address",
            "token_id",
            "image_url",
            "rarity_score",
            "rank",
            "buy_rank",
            "raw_metadata",
            "trait_count",
        )

    def get_contract_address(self, obj):
        return obj.collection.contract_address


class WalletNFTSerializer(serializers.ModelSerializer):
    nft = NFTSerializer()
    collection_thumbnail = serializers.SerializerMethodField()
    token_floor_price = serializers.SerializerMethodField()

    class Meta:
        model = WalletNFT
        fields = (
            "id",
            "nft",
            "collection_thumbnail",
            "token_floor_price",
        )
        read_only_fields = (
            "id",
            "nft",
            "collection_thumbnail",
            "token_floor_price",
        )

    def get_collection_thumbnail(self, obj: WalletNFT):
        nft = obj.nft
        if not nft:
            return None
        thumbnail = obj.nft.collection.thumbnail
        if thumbnail:
            return thumbnail.url
        return None

    def get_token_floor_price(self, obj: WalletNFT):
        nft = obj.nft
        if not nft:
            return None
        try:
            return obj.nft.collection.collectionmetrics.current_floor_price
        except CollectionMetrics.DoesNotExist:
            return None


class ExtendedNFTSerializer(serializers.ModelSerializer):
    collection = CollectionDetailSerializer()

    class Meta:
        model = NFT
        fields = (
            "collection",
            "token_id",
            "image_url",
            "rarity_score",
            "rank",
            "buy_rank",
            "raw_metadata",
            "trait_count",
        )
        read_only_fields = (
            "collection",
            "token_id",
            "image_url",
            "rarity_score",
            "rank",
            "buy_rank",
            "raw_metadata",
            "trait_count",
        )


class CollectionTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ("name", "contract_address")
        read_only_fields = ("name", "contract_address")


class NFTTransactionSerializer(serializers.ModelSerializer):
    collection = CollectionTransactionSerializer()

    class Meta:
        model = NFT
        fields = ("name", "token_id", "raw_metadata", "collection")
        read_only_fields = ("name", "token_id", "raw_metadata", "collection")


class TransactionSerializer(serializers.ModelSerializer):
    nft = NFTTransactionSerializer()

    class Meta:
        model = Transaction
        fields = (
            "id",
            "nft",
            "transaction_type",
            "transfer_from",
            "transfer_to",
            "contract_address",
            "token_id",
            "quantity",
            "transaction_hash",
            "block_hash",
            "block_number",
            "transaction_date",
            "price_eth",
            "price_usd",
        )
        read_only_fields = (
            "id",
            "nft",
            "transaction_type",
            "transfer_from",
            "transfer_to",
            "contract_address",
            "token_id",
            "quantity",
            "transaction_hash",
            "block_hash",
            "block_number",
            "transaction_date",
            "price_eth",
            "price_usd",
        )


class UserWhiteListSerializer(serializers.ModelSerializer):
    collection = CollectionDetailSerializer()

    class Meta:
        model = UserWhiteList
        fields = (
            "id",
            "collection",
        )


class UserWhiteListCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserWhiteList
        fields = ("id", "collection")
        read_only_fields = ("id",)


class WalletSelectedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("id", "wallet_address", "thumbnail", "ens_domain")
        read_only_fields = ("id", "wallet_address", "thumbnail", "ens_domain")


class TrackedWalletSerializer(serializers.ModelSerializer):
    selected_state = serializers.SerializerMethodField()
    wallet = WalletSelectedSerializer()
    user_tracked_wallet_id = serializers.SerializerMethodField()

    class Meta:
        model = TrackedWallet
        fields = ("id", "wallet", "selected_state", "user_tracked_wallet_id")
        read_only_fields = ("id", "wallet", "selected_state", "user_tracked_wallet_id")

    def get_selected_state(self, obj):
        tracked_wallet_ids = self.context["tracked_wallet_ids"]
        return obj.id in tracked_wallet_ids

    def get_user_tracked_wallet_id(self, obj: TrackedWallet):
        user = self.context["user"]
        try:
            utw = UserTrackedWallet.objects.get(tracked_wallet=obj, user=user)
            return utw.id
        except UserTrackedWallet.DoesNotExist:
            return None


class UserTrackedWalletSerializer(serializers.ModelSerializer):

    tracked_wallet = TrackedWalletSerializer()

    class Meta:
        model = UserTrackedWallet
        fields = ("id", "name", "tracked_wallet")
        read_only_fields = ("id", "name", "tracked_wallet")


class UserTrackedWalletCreateSerializer(serializers.Serializer):
    wallet_address = serializers.CharField()
    name = serializers.CharField(required=False)


class CollectionTransferNFTSerializer(serializers.ModelSerializer):
    class Meta:
        model = NFT
        fields = ("id", "name", "rank", "token_id", "raw_metadata")
        read_only_fields = ("id", "name", "rank", "token_id", "raw_metadata")


class CollectionTransferSerializer(serializers.ModelSerializer):
    nft = CollectionTransferNFTSerializer()

    class Meta:
        model = Transaction
        fields = (
            "id",
            "nft",
            "transaction_type",
            "transfer_from",
            "transfer_to",
            "quantity",
            "transaction_hash",
            "transaction_date",
            "price_eth",
            "price_usd",
        )
        read_only_fields = (
            "id",
            "nft",
            "transaction_type",
            "transfer_from",
            "transfer_to",
            "quantity",
            "transaction_hash",
            "transaction_date",
            "price_eth",
            "price_usd",
        )
