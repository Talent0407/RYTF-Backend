from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models.signals import post_save, pre_save
from siwe_auth.models import Wallet as UserWallet

User = get_user_model()


class DiscordUserOAuth2Manager(models.Manager):
    def create_new_discord_user(self, data, user):
        discord_tag = "{}#{}".format(data["username"], data["discriminator"])
        new_user = DiscordUser(
            user=user,
            id=data["id"],
            username=data["username"],
            avatar=data["avatar"],
            public_flags=data["public_flags"],
            flags=data["flags"],
            locale=data["locale"],
            mfa_enabled=data["mfa_enabled"],
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            discord_tag=discord_tag,
            raw_response_data=data,
        )
        new_user.save()
        return new_user


class DiscordUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    discord_tag = models.CharField(max_length=100)
    avatar = models.CharField(max_length=100, blank=True, null=True)
    public_flags = models.IntegerField()
    flags = models.IntegerField()
    locale = models.CharField(max_length=100)
    mfa_enabled = models.BooleanField()
    is_beta_tester = models.BooleanField(default=False)
    access_token = models.CharField(max_length=100, null=True, blank=True)
    refresh_token = models.CharField(max_length=100, null=True, blank=True)
    raw_response_data = models.JSONField()
    objects = DiscordUserOAuth2Manager()


class RequestLog(models.Model):
    endpoint = models.CharField(max_length=100, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    response_code = models.PositiveSmallIntegerField()
    method = models.CharField(max_length=10, null=True)
    remote_address = models.CharField(max_length=20, null=True)  # IP address of user
    exec_time = models.IntegerField(null=True)  # Time taken to create the response
    date = models.DateTimeField(auto_now=True)  # Date and time of request
    body_response = models.TextField()
    body_request = models.TextField()
    headers = models.TextField()

    def __str__(self):
        return str(self.date)


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    wallet_address = models.CharField(max_length=100, unique=True)
    nfts_raw_data = models.JSONField(blank=True, null=True)
    is_member = models.BooleanField(default=False)
    is_beta = models.BooleanField(default=False)

    # A user can only have one active wallet at a time
    active = models.BooleanField(default=True)
    processed = models.BooleanField(default=False)
    display_name = models.CharField(max_length=100, blank=True, null=True)
    thumbnail = models.TextField(blank=True, null=True)
    custom_thumbnail = models.ImageField(
        upload_to="wallet_custom_thumbnails/", blank=True, null=True
    )
    ens_domain = models.CharField(max_length=150, blank=True, null=True)
    ens_domains = models.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return self.wallet_address

    @property
    def has_access(self):
        return self.is_beta or self.is_member


def post_save_user_receiver(sender, instance, created, *args, **kwargs):
    if created:
        from ryft.core.portfolio.tasks import run_new_wallet_tasks

        user: UserWallet = instance
        wallet, created = Wallet.objects.get_or_create(
            user=user, wallet_address=user.ethereum_address.lower(), active=True
        )
        TrackedWallet.objects.get_or_create(wallet=wallet)
        transaction.on_commit(lambda: run_new_wallet_tasks(wallet.wallet_address))


post_save.connect(post_save_user_receiver, sender=UserWallet)


class Collection(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    contract_abi = models.TextField(blank=True, null=True)
    contract_address = models.CharField(max_length=100, unique=True)
    supply = models.PositiveIntegerField(blank=True, null=True)
    mint_date = models.DateTimeField(blank=True, null=True)
    mint_price = models.CharField(max_length=100, blank=True, null=True)
    released = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    dead = models.BooleanField(default=False)
    discord_link = models.URLField(max_length=100, blank=True, null=True)
    twitter_link = models.URLField(max_length=100, blank=True, null=True)
    website_link = models.URLField(max_length=100, blank=True, null=True)
    opensea_link = models.URLField(max_length=100, blank=True, null=True)
    num_discord_members = models.PositiveIntegerField(blank=True, null=True)
    num_twitter_followers = models.PositiveIntegerField(blank=True, null=True)
    thumbnail = models.ImageField(
        upload_to="collection_thumbnails/", blank=True, null=True
    )
    community_submitted = models.BooleanField(default=False)
    nftport_unsupported = models.BooleanField(default=False)
    created_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


def pre_save_collection_receiver(sender, instance, *args, **kwargs):
    instance.contract_address = instance.contract_address.lower()


class CollectionVote(models.Model):
    VOTE_CHOICES = (
        ("Up", "Up"),
        ("Down", "Down"),
    )

    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="votes"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=10, choices=VOTE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.collection.name


def post_save_collection_receiver(sender, instance, created, *args, **kwargs):
    if created:
        if instance.contract_address:
            from .tasks import calculate_collection_rarity_task

            transaction.on_commit(
                lambda: calculate_collection_rarity_task(instance.contract_address)
            )


post_save.connect(post_save_collection_receiver, sender=Collection)
pre_save.connect(pre_save_collection_receiver, sender=Collection)


class ArtworkPreviewImage(models.Model):
    image = models.ImageField(upload_to="artwork_previews/", blank=True, null=True)
    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="artwork_images"
    )

    def __str__(self) -> str:
        if self.image:
            return self.image.name
        return "No image"


class CollectionMetrics(models.Model):
    collection = models.OneToOneField(Collection, on_delete=models.CASCADE)
    current_floor_price = models.FloatField(blank=True, null=True)
    average_price_24hr = models.FloatField(blank=True, null=True)
    average_sales_24hr = models.FloatField(blank=True, null=True)
    average_volume_24hr = models.FloatField(blank=True, null=True)
    listings_24hr = models.IntegerField(blank=True, null=True)
    sales_24hr = models.IntegerField(blank=True, null=True)
    delists_24hr = models.IntegerField(blank=True, null=True)
    royalty_fee = models.FloatField(blank=True, null=True)
    price_history = models.JSONField(blank=True, null=True)
    owners_history = models.JSONField(blank=True, null=True)
    last_fetched = models.DateTimeField()

    def __str__(self) -> str:
        return self.collection.name


class NFT(models.Model):
    """
    Represents an NFT part of a collection and its rarity metrics
    """

    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="nfts"
    )
    name = models.TextField(blank=True, null=True)
    token_id = models.TextField()
    image_url = models.TextField(blank=True, null=True)
    rarity_score = models.FloatField(null=True, blank=True)
    rank = models.IntegerField(null=True, blank=True)
    buy_rank = models.IntegerField(null=True, blank=True)
    raw_metadata = models.JSONField(null=True, blank=True)
    trait_count = models.IntegerField(default=0)

    def __str__(self) -> str:
        return self.token_id


class CollectionAttribute(models.Model):
    """
    Represents the possible attributes of an NFT Collection
    """

    collection = models.ForeignKey(
        Collection, on_delete=models.CASCADE, related_name="attributes"
    )
    name = models.TextField()
    value = models.TextField()
    occurrences = models.IntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.name}: {self.value}"


class NFTTrait(models.Model):
    """
    Represents the metadata traits of an NFT
    """

    nft = models.ForeignKey(NFT, on_delete=models.CASCADE, related_name="traits")
    attribute = models.ForeignKey(
        CollectionAttribute, on_delete=models.CASCADE, related_name="collection_traits"
    )
    rarity_score = models.FloatField(null=True)

    def __str__(self) -> str:
        return f"{self.attribute.name}: {self.attribute.value}"


class WalletNFT(models.Model):
    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="wallet_nfts"
    )
    nft = models.ForeignKey(NFT, on_delete=models.CASCADE, blank=True, null=True)
    nft_raw_data = models.JSONField()

    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(
    #             fields=["wallet", "nft"], name="NFT can only belong to one Wallet"
    #         )
    #     ]

    def __str__(self):
        return str(self.id)


class WalletPortfolioRecord(models.Model):
    """Represents a daily record of the wallet portfolio value"""

    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="wallet_portfolios"
    )
    timestamp = models.DateTimeField()
    portfolio_value = models.FloatField(default=0)

    def __str__(self):
        return self.wallet.wallet_address


class Transaction(models.Model):
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
        blank=True,
        null=True,
    )
    nft = models.ForeignKey(
        NFT,
        on_delete=models.CASCADE,
        related_name="nft_transactions",
        blank=True,
        null=True,
    )
    transaction_type = models.CharField(max_length=50)
    transfer_from = models.CharField(max_length=200, blank=True, null=True)
    transfer_to = models.CharField(max_length=200, blank=True, null=True)
    contract_address = models.CharField(max_length=100, blank=True, null=True)
    token_id = models.CharField(max_length=200)
    quantity = models.IntegerField(default=1)
    transaction_hash = models.CharField(max_length=67, blank=True, null=True)
    block_hash = models.CharField(max_length=200, blank=True, null=True)
    block_number = models.IntegerField(default=0, blank=True, null=True)
    transaction_date = models.DateTimeField()
    raw_transaction_data = models.JSONField(blank=True, null=True)
    price_eth = models.FloatField(blank=True, null=True)
    price_usd = models.FloatField(blank=True, null=True)

    # Transfers that show only on the collection page
    collection_only = models.BooleanField(default=False)

    def __str__(self):
        return self.token_id


class UserWhiteList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="whitelists")
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "collection")

    def __str__(self):
        return str(self.id)


class EthBlock(models.Model):
    last_block = models.PositiveIntegerField()
    timestamp = models.DateTimeField()
    contract_address = models.TextField()

    def __str__(self):
        return str(self.last_block)


class TrackedWallet(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.SET_NULL, blank=True, null=True)
    thumbnail = models.URLField(blank=True, null=True)

    def __str__(self):
        if self.wallet:
            return self.wallet.wallet_address
        return str(self.id)


class UserTrackedWallet(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="tracked_wallets"
    )
    name = models.CharField(max_length=100, blank=True, null=True)
    tracked_wallet = models.ForeignKey(TrackedWallet, on_delete=models.CASCADE)
    created_timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "tracked_wallet")

    def __str__(self):
        return str(self.id)


class APICallRecordLog(models.Model):
    client = models.CharField(max_length=50)
    service = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.client


class TrendingCollections(models.Model):
    trending_by_volume = models.JSONField(blank=True, null=True)
    trending_by_sales = models.JSONField(blank=True, null=True)
    trending_by_price = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.timestamp)


class EthPrice(models.Model):
    date = models.DateField()
    value = models.DecimalField(decimal_places=2, max_digits=10)

    def __str__(self):
        return str(self.value)
