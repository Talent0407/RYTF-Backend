from django.contrib import admin
from django.db.models import QuerySet

from ryft.core.portfolio.tasks import run_new_wallet_tasks
from ryft.core.tasks import (
    calculate_collection_rarity_task,
    link_nfts_to_transactions,
    link_nfts_to_wallets,
)

from .forms import CollectionAdminForm
from .models import (
    NFT,
    APICallRecordLog,
    ArtworkPreviewImage,
    Collection,
    CollectionAttribute,
    CollectionMetrics,
    DiscordUser,
    EthBlock,
    EthPrice,
    NFTTrait,
    RequestLog,
    TrackedWallet,
    Transaction,
    TrendingCollections,
    UserTrackedWallet,
    UserWhiteList,
    Wallet,
    WalletNFT,
    WalletPortfolioRecord,
)


def collection_link_nfts_to_transactions(
    modeladmin, request, queryset: QuerySet[Collection]
):
    for collection in queryset:
        link_nfts_to_transactions.delay(collection.contract_address)


collection_link_nfts_to_transactions.short_description = "Link NFTs to Transactions"


def collection_link_nfts_to_wallets(
    modeladmin, request, queryset: QuerySet[Collection]
):
    for collection in queryset:
        link_nfts_to_wallets.delay(collection.contract_address)


collection_link_nfts_to_wallets.short_description = "Link NFTs to Wallets"


def collection_perform_all_tasks(modeladmin, request, queryset: QuerySet[Collection]):
    for collection in queryset:
        calculate_collection_rarity_task(collection.contract_address)


collection_perform_all_tasks.short_description = "Perform all tasks"


def wallet_calculate_wallet_portfolio_task(
    modeladmin, request, queryset: QuerySet[Wallet]
):
    for wallet in queryset:
        run_new_wallet_tasks(wallet.wallet_address)


wallet_calculate_wallet_portfolio_task.short_description = "Perform all tasks"


class WalletAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "wallet_address",
        "active",
        "is_member",
        "is_beta",
        "processed",
    ]
    exclude = ["nfts_raw_data"]
    search_fields = ["wallet_address"]
    actions = [wallet_calculate_wallet_portfolio_task]


class ArtworkPreviewImageInLineAdmin(admin.TabularInline):
    model = ArtworkPreviewImage
    extra = 0


class CollectionAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "contract_address",
        "supply",
        "mint_date",
        "released",
        "verified",
    ]
    search_fields = ["name", "contract_address"]
    inlines = [ArtworkPreviewImageInLineAdmin]
    actions = [
        collection_link_nfts_to_transactions,
        collection_link_nfts_to_wallets,
        collection_perform_all_tasks,
    ]
    add_form = CollectionAdminForm

    def get_form(self, request, obj=None, **kwargs):
        """
        Use CollectionAdminForm when creating
        """
        defaults = {}
        if obj is None:
            defaults["form"] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)


class CollectionMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "collection",
        "current_floor_price",
        "average_price_24hr",
        "average_sales_24hr",
        "average_volume_24hr",
        "listings_24hr",
        "sales_24hr",
        "delists_24hr",
        "royalty_fee",
    ]
    search_fields = ["collection__name", "collection__contract_address"]


class NFTTraitInLineAdmin(admin.TabularInline):
    model = NFTTrait
    extra = 0
    can_delete = False
    show_change_link = False


class NFTAdmin(admin.ModelAdmin):
    list_display = [
        "token_id",
        "id",
        "rarity_score",
        "rank",
        "buy_rank",
    ]
    exclude = ["raw_metadata"]
    search_fields = ["token_id", "collection__contract_address"]
    inlines = [NFTTraitInLineAdmin]


class WalletPortfolioRecordAdmin(admin.ModelAdmin):
    list_display = [
        "wallet",
        "timestamp",
        "portfolio_value",
    ]
    search_fields = ["wallet__wallet_address"]


class WalletNFTAdmin(admin.ModelAdmin):
    list_display = ["id"]
    search_fields = ["wallet__wallet_address", "nft__collection__contract_address"]
    exclude = ["nft_raw_data"]


class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "transaction_type", "block_number"]
    search_fields = ["wallet__wallet_address"]
    raw_id_fields = ["wallet", "nft"]


class CollectionAttributeAdmin(admin.ModelAdmin):
    list_display = ["name", "value", "occurrences"]
    search_fields = ["name", "value", "collection__contract_address"]


class APICallRecordLogAdmin(admin.ModelAdmin):
    list_display = [
        "client",
        "service",
        "timestamp",
    ]
    list_filter = ["client", "service"]


class UserTrackedWalletAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "name",
        "tracked_wallet",
    ]


class EthBlockAdmin(admin.ModelAdmin):
    list_display = ["last_block", "contract_address"]


class EthPriceAdmin(admin.ModelAdmin):
    list_display = ["date", "value"]


class DiscordUserAdmin(admin.ModelAdmin):
    list_display = ["id", "username"]
    exclude = ["access_token", "refresh_token"]


class RequestLogAdmin(admin.ModelAdmin):
    list_display = ["user", "endpoint", "method", "date"]


class TrackedWalletAdmin(admin.ModelAdmin):
    list_display = ["id", "__str__"]


admin.site.login_template = "siwe_auth/login.html"
admin.site.register(DiscordUser, DiscordUserAdmin)
admin.site.register(Wallet, WalletAdmin)
admin.site.register(Collection, CollectionAdmin)
admin.site.register(CollectionMetrics, CollectionMetricsAdmin)
admin.site.register(NFT, NFTAdmin)
admin.site.register(CollectionAttribute, CollectionAttributeAdmin)
admin.site.register(NFTTrait)
admin.site.register(WalletPortfolioRecord, WalletPortfolioRecordAdmin)
admin.site.register(WalletNFT, WalletNFTAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(UserWhiteList)
admin.site.register(EthBlock, EthBlockAdmin)
admin.site.register(TrackedWallet, TrackedWalletAdmin)
admin.site.register(UserTrackedWallet, UserTrackedWalletAdmin)
admin.site.register(APICallRecordLog, APICallRecordLogAdmin)
admin.site.register(TrendingCollections)
admin.site.register(EthPrice, EthPriceAdmin)
admin.site.register(RequestLog, RequestLogAdmin)
