import logging
import time

from celery import chain
from dateutil import parser
from django.conf import settings
from django.core.mail import send_mail
from django.db import connection
from django.utils import timezone

from config.celery_app import app
from ryft.core.integrations.alchemy import get_alchemy_client
from ryft.core.integrations.errors import NFTPortContractNotFound
from ryft.core.integrations.mnemonic import mnemonic_client
from ryft.core.integrations.nftport import nftport_client
from ryft.core.models import (
    NFT,
    APICallRecordLog,
    Collection,
    CollectionMetrics,
    EthBlock,
    TrackedWallet,
    Transaction,
    Wallet,
    WalletNFT,
    WalletPortfolioRecord,
)
from ryft.core.services.logging import logging_service


def send_contract_dne_mail(contract_addresses):
    addresses_str = ""
    for c in contract_addresses:
        addresses_str += f"{c}\n"
    send_mail(
        subject="A contract is missing",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.SUPPORT_EMAIL],
        message="A contract is missing/incomplete. The contract addresses are:"
        + addresses_str
        + "\n"
        + "Please go to the backend admin and fill in the missing information.",
    )


@app.task
def dummy_task():
    return "OK"


@app.task(name="get_wallet_nfts")
def get_wallet_nfts(wallet_id, should_fetch=True):
    logging.info(msg="Fetching wallet NFTs")

    if should_fetch is not True:
        return False

    wallet = Wallet.objects.get(id=wallet_id)

    # Fetch all NFTs for this wallet
    owned_nfts = []

    page_limit = 500
    has_next_page = True
    offset = 0
    while has_next_page:
        data = mnemonic_client.get_wallet_nfts(
            wallet.wallet_address, limit=page_limit, offset=offset
        )
        time.sleep(1)
        APICallRecordLog.objects.create(client="mnemonic", service="get_wallet_nfts")
        logging_service.log(
            {
                "Event": "Fetch Wallet NFTs",
                "Service": "Mnemonic",
                "Wallet_Address": wallet.wallet_address,
            }
        )
        nfts = data.get("tokens")
        if nfts:
            result_length = len(nfts)
            owned_nfts += nfts
            if result_length < page_limit:
                has_next_page = False
            else:
                offset += 500
        else:
            has_next_page = False

    # Store the NFTs in JSON for now in the wallet
    wallet.nfts_raw_data = owned_nfts
    wallet.save()

    connection.close()

    logging.info(msg="Completed fetching wallet NFTs")
    return "Done"


@app.task(name="calculate_portfolio_total")
def calculate_portfolio_total(wallet_id):
    logging.info(msg=f"Calculating portfolio for wallet {wallet_id}")
    wallet = Wallet.objects.get(id=wallet_id)

    contract_addresses = []
    if not wallet.nfts_raw_data:
        logging.warning(
            msg=f"Wallet: {wallet.wallet_address} does not have raw nft data"
        )
        return "Done"

    for nft in wallet.nfts_raw_data:
        contract_addresses.append(nft.get("contractAddress"))

    contract_addresses = list(set(contract_addresses))

    metrics = (
        CollectionMetrics.objects.select_related("collection")
        .filter(collection__contract_address__in=contract_addresses)
        .values("collection__contract_address", "current_floor_price")
    )

    floor_price_map = {}
    for collection_metric in metrics:
        floor_price_map[
            collection_metric["collection__contract_address"]
        ] = collection_metric["current_floor_price"]

    collection_floor_prices = []

    for nft in wallet.nfts_raw_data:
        contract_address = nft.get("contractAddress")
        if contract_address:
            # Check the floor price and add to list
            floor_price = floor_price_map.get(contract_address)
            if floor_price:
                collection_floor_prices.append(floor_price)

    # Calculate portfolio value
    portfolio_value = sum(collection_floor_prices)
    WalletPortfolioRecord.objects.create(
        wallet=wallet, portfolio_value=portfolio_value, timestamp=timezone.now()
    )
    logging.info(msg=f"Finished calculating portfolio for wallet {wallet_id}")

    connection.close()

    return portfolio_value


@app.task(name="create_wallet_nfts")
def create_wallet_nfts(wallet_id, should_create=True):
    logging.info(msg="Creating wallet NFTs")

    if should_create is not True:
        return False

    wallet = Wallet.objects.get(id=wallet_id)
    if not wallet.nfts_raw_data:
        return "Wallet has no raw data"

    # Delete and recreate them all
    wallet.wallet_nfts.all().delete()

    wallet_nfts = []
    # Only getting the first 100. We can process the remaining in a separate task
    # Also worth looking at how this would affect amount of data being stored
    for nft_data in list(wallet.nfts_raw_data)[0:100]:
        contract_address = nft_data["contractAddress"]
        token_id = nft_data["tokenId"]

        try:
            collection = Collection.objects.get(contract_address=contract_address)
            nft_obj = NFT.objects.get(token_id=token_id, collection=collection)
        except (NFT.DoesNotExist, Collection.DoesNotExist):
            nft_obj = None

        metadata = nft_data.get("metadata")

        nft_raw_data = {}
        if metadata:
            nft_raw_data = {
                "contract_address": contract_address,
                "token_id": token_id,
            }
        else:
            logging.warning(
                msg=f"Couldn't get metadata for NFT in wallet: {wallet_id}: {metadata}"
            )

        wallet_nfts.append(
            WalletNFT(wallet=wallet, nft_raw_data=nft_raw_data, nft=nft_obj)
        )

    WalletNFT.objects.bulk_create(wallet_nfts, batch_size=100)
    logging.info(msg=f"Created Wallet NFTs for wallet {wallet.wallet_address}")

    connection.close()

    logging.info(msg="Finished creating wallet NFTs")
    return "Done"


@app.task(name="fetch_individual_wallet_transactions")
def fetch_individual_wallet_transactions(wallet_id):
    logging.info(
        msg=f"Starting task to fetch individual wallet transactions for wallet: {wallet_id}"
    )
    wallet = Wallet.objects.get(id=wallet_id)
    alchemy_client = get_alchemy_client()

    eth_blocks_per_day = 6200
    days_ago = 14
    latest_block_number = (
        int(EthBlock.objects.order_by("-last_block").first().last_block)
        - days_ago * eth_blocks_per_day
    )
    # latest_transaction = (
    #     Transaction.objects.filter(wallet=wallet).order_by("-block_number").first()
    # )
    # if latest_transaction:
    #     latest_block_number = latest_transaction.block_number

    def fetch_transactions(transaction_type: str):
        _transactions = []
        has_next_page = True
        while has_next_page:
            result = alchemy_client.get_wallet_transactions(
                wallet.wallet_address,
                last_block=latest_block_number,
                transaction_type=transaction_type,
            )
            time.sleep(5)
            data = result["result"]
            for tsx in data["transfers"]:
                block_num = int(tsx["blockNum"], base=16)

                if block_num <= latest_block_number:
                    logging.info(
                        msg=f"Stopped fetching transactions for wallet {wallet_id} because we've "
                        f"reached block number {block_num}"
                    )
                    # stop because we have transactions from this block number and onwards
                    has_next_page = False
                else:
                    _transactions.append(tsx)

            page = data.get("pageKey")
            if not page:
                has_next_page = False
        return _transactions

    received_transactions = fetch_transactions("receiver")
    sent_transactions = fetch_transactions("sender")
    transactions = received_transactions + sent_transactions
    null_address = "0x0000000000000000000000000000000000000000"

    def get_transaction_type(t):
        transaction_type = "transfer"
        from_address = t.get("from")
        to_address = t.get("to")

        if from_address == null_address:
            transaction_type = "mint"

        elif to_address == null_address:
            transaction_type = "burn"

        elif from_address == wallet.wallet_address:
            transaction_type = "sale"

        elif to_address == wallet.wallet_address:
            transaction_type = "buy"

        return transaction_type

    transaction_objs = []
    for t in transactions:
        contract_address = t["rawContract"].get("address")
        block_number = int(t["blockNum"], base=16)
        token_id_string = t.get("tokenId")
        if not token_id_string:
            # try get from erc1155
            erc115 = t.get("erc1155Metadata")
            if erc115:
                if len(erc115) > 0:
                    token_id_string = erc115[0].get("tokenId")

        from_address = t.get("from")
        to_address = t.get("to")

        if contract_address and token_id_string:
            token_id = int(token_id_string, base=16)
            transaction_obj = Transaction(
                wallet=wallet,
                nft=(
                    NFT.objects.filter(
                        collection__contract_address=contract_address, token_id=token_id
                    ).first()
                ),
                transfer_from=from_address,
                transfer_to=to_address,
                transaction_type=get_transaction_type(t),
                contract_address=t.get("rawContract").get("address"),
                token_id=token_id,
                quantity=1,
                transaction_hash=t.get("hash"),
                block_number=block_number,
                transaction_date=parser.parse(t.get("metadata").get("blockTimestamp")),
                raw_transaction_data=t,
            )
            transaction_objs.append(transaction_obj)

    Transaction.objects.bulk_create(transaction_objs, batch_size=100)
    logging.info(msg=f"Created Transactions for wallet {wallet.wallet_address}")

    # This tells us if the wallet has any new transactions

    connection.close()

    return len(transaction_objs) > 0


@app.task(name="check_wallet_access")
def check_wallet_access(wallet_id):
    logging.info(msg="Checking wallet access")
    wallet = Wallet.objects.get(id=wallet_id)
    ryft_collection = Collection.objects.get(
        contract_address=settings.RYFT_CONTRACT_ADDRESS
    )

    wallet_nfts = wallet.wallet_nfts.filter(nft__collection=ryft_collection)

    owns_ryft_nft = wallet_nfts.exists()

    if owns_ryft_nft:
        wallet.is_member = True
        wallet.save()

    connection.close()
    logging.info(msg="Finished checking wallet access")
    return "Done"


@app.task(name="save_final_wallet_details")
def save_final_wallet_details(wallet_id):
    logging.info(msg="Saving final details on wallet")
    wallet = Wallet.objects.get(id=wallet_id)
    wallet.processed = True
    wallet.save()

    ens_data = mnemonic_client.get_ens_domains(wallet.wallet_address)
    entities = ens_data.get("entities")
    if entities:
        if len(entities) > 0:
            wallet.ens_domains = entities
            first_domain = entities[0]
            wallet.ens_domain = first_domain.get("name")

    connection.close()
    logging.info(msg="Finished saving final details on wallet")

    return "Done"


@app.task(name="save_tracked_wallet_thumbnail")
def create_tracked_wallet(wallet_id):
    logging.info(msg="Creating tracked wallet")

    wallet = Wallet.objects.get(id=wallet_id)
    tracked_wallet, created = TrackedWallet.objects.get_or_create(wallet=wallet)

    wallet_nfts_with_thumbnails = (
        wallet.wallet_nfts.select_related("nft", "nft__collection__collectionmetrics")
        .filter(nft__raw_metadata__metadata__image__isnull=False)
        .order_by("-nft__collection__collectionmetrics__current_floor_price")
    )

    if wallet_nfts_with_thumbnails.exists():
        for wallet_nft in wallet_nfts_with_thumbnails:
            nft = wallet_nft.nft
            if nft.image_url:
                if "ipfs" not in nft.image_url:
                    tracked_wallet.thumbnail = nft.image_url
                    tracked_wallet.save()
                    wallet.thumbnail = nft.image_url
                    wallet.save()
                    break

                    # TODO redo wallet thumbnail if sold the NFT

    connection.close()
    logging.info(msg="Finished creating tracked wallet")
    return "Done"


def calculate_wallet_portfolio(wallet_address, tracked_wallet=False):
    """
    This gets triggered after adding the wallet
    """
    wallet = Wallet.objects.get(wallet_address=wallet_address)

    if tracked_wallet:
        # Step 1 - create webhook for events
        step1 = create_wallet_webhook.si(wallet.wallet_address)

        # Step 2 - get NFTs - store's raw data on the wallet
        step2 = get_wallet_nfts.si(wallet.id)

        # Step 3 - create WalletNFTs for the wallet
        step3 = create_wallet_nfts.si(wallet.id)

        # Step 4 - fetch transactions of this wallet (doesn't impact portfolio calculations)
        step4 = fetch_individual_wallet_transactions.si(wallet.id)

        # Step 5 - done processing
        step5 = save_final_wallet_details.si(wallet.id)

        # Step 6 - create tracked wallet
        step6 = create_tracked_wallet.si(wallet.id)

        workflow = chain(step1, step2, step3, step4, step5, step6)
        result = workflow.delay()
        return result

    # Step 0 - create webhook for events
    step0 = create_wallet_webhook.si(wallet.wallet_address)

    # Step 1 - get NFTs - store's raw data on the wallet
    step1 = get_wallet_nfts.si(wallet.id)

    # Step 2 - create WalletNFTs for the wallet
    step2 = create_wallet_nfts.si(wallet.id)

    # Step 3 - calculate portfolio value from floor prices
    step3 = calculate_portfolio_total.si(wallet.id)

    # Step 4 - fetch transactions of this wallet (doesn't impact portfolio calculations)
    step4 = fetch_individual_wallet_transactions.si(wallet.id)

    # Step 5 - check the wallet has an NFT for ryft
    step5 = check_wallet_access.si(wallet.id)

    # Step 6 - done processing
    step6 = save_final_wallet_details.si(wallet.id)

    # Step 7 - create tracked wallet
    step7 = create_tracked_wallet.si(wallet.id)

    workflow = chain(step0, step1, step2, step3, step4, step5, step6, step7)
    result = workflow.delay()
    return result


def run_new_wallet_tasks(wallet_address, tracked_wallet=False):
    # This function exists so that we can mock the calculate_wallet_portfolio task
    calculate_wallet_portfolio(wallet_address, tracked_wallet)


@app.task(name="fetch_collection_metrics")
def fetch_collection_metrics():
    """
    Daily task that fetches collection statistics
    """
    collections = Collection.objects.filter(released=True, nftport_unsupported=False)

    for collection in collections:
        time.sleep(3)

        contract_address = collection.contract_address
        try:
            nftport_resp = nftport_client.get_contract_statistics(contract_address)
            APICallRecordLog.objects.create(
                client="nftport", service="fetch_nftport_statistics"
            )
            logging_service.log(
                {
                    "Event": "Fetch Statistics",
                    "Service": "NFTPort",
                    "Collection_ID": collection.id,
                    "Collection_Name": collection.name,
                    "Contract_Address": contract_address,
                }
            )
            nftport_data = nftport_resp.get("statistics")
            if nftport_data:
                metrics, created = CollectionMetrics.objects.get_or_create(
                    collection=collection, defaults={"last_fetched": timezone.now()}
                )
                metrics.current_floor_price = nftport_data.get("floor_price")
                metrics.average_price_24hr = nftport_data.get("one_day_average_price")
                metrics.average_sales_24hr = nftport_data.get("one_day_sales")
                metrics.average_volume_24hr = nftport_data.get("one_day_volume")
                metrics.last_fetched = timezone.now()
                metrics.save()

        except NFTPortContractNotFound:
            collection.nftport_unsupported = True
            collection.save()
            return

    connection.close()


@app.task(name="wallet_callback")
def wallet_callback(w_id):
    return f"Completed daily task for wallet: {w_id}"


def daily_wallet_task():
    wallet_ids = list(Wallet.objects.all().values_list("id", flat=True))
    for wallet_id in wallet_ids:
        calculate_portfolio_total.apply_async((wallet_id,))

    # step1 = group([calculate_portfolio_total.s(wallet_id) for wallet_id in wallet_ids])
    #
    # step1.skew(start=1, stop=len(wallet_ids))()


@app.task(name="create_wallet_webhook")
def create_wallet_webhook(wallet_address):
    client = get_alchemy_client()
    client.create_webhook_address(wallet_address)
    logging.info(msg="Created webhook for wallet")


@app.task(name="wallet_transaction_callback")
def wallet_transaction_callback(w_id):
    return f"Completed task for wallet transactions: {w_id}"


@app.task(name="fetch_ryft_owners_task")
def fetch_ryft_owners_task():
    logging.info(msg="Fetching Ryft NFT owners")
    client = get_alchemy_client()
    owners = client.get_ryft_collection_owners()
    owner_addresses = owners["ownerAddresses"]

    # lookup who has an account and give them access
    wallets_with_access = Wallet.objects.filter(wallet_address__in=owner_addresses)
    wallets_with_access.update(is_member=True)

    # set the rest of the wallets to not have access
    wallets_without_access = Wallet.objects.exclude(wallet_address__in=owner_addresses)
    wallets_without_access.update(is_member=False)
    logging.info(msg="Updated Ryft NFT owners")

    connection.close()


@app.task(name="send_daily_collection_email")
def send_daily_collection_email():
    """
    Sends a daily email containing a list of missing collections
    """

    wallet_addresses = (
        WalletNFT.objects.all()
        .values_list("nft_raw_data__contract_address", flat=True)
        .distinct()
    )

    all_addresses = Collection.objects.filter(released=True).values_list(
        "contract_address", flat=True
    )
    new_addresses = [
        a for a in wallet_addresses if a not in all_addresses and a is not None
    ]

    send_contract_dne_mail(new_addresses)

    connection.close()


"""
# Example of a complex workflow -> Runs a chain of tasks for all wallets.
# Completes each chain before moving to the next wallet

wallet_workflows = []
for wallet_id in wallet_ids:

    wallet_workflow = chord(
        (fetch_individual_wallet_transactions.si(wallet_id)),
        wallet_callback.si(wallet_id)
    )
    wallet_workflows.append(wallet_workflow)

workflow = chain(wallet_workflows)
workflow.delay()
"""
