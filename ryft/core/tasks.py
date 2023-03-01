import datetime
import logging
import time
from collections.abc import Mapping

from celery import chain
from dateutil import parser
from django.db import connection
from django.db.models import QuerySet
from pycoingecko import CoinGeckoAPI

from config.celery_app import app
from ryft.core.integrations.alchemy import get_alchemy_client
from ryft.core.integrations.mnemonic import TrendingBy, mnemonic_client
from ryft.core.models import (
    NFT,
    APICallRecordLog,
    Collection,
    CollectionAttribute,
    CollectionMetrics,
    EthBlock,
    EthPrice,
    Transaction,
    TrendingCollections,
    WalletNFT,
)
from ryft.core.services.logging import logging_service


@app.task(name="rank_nfts")
def rank_nfts(contract_address):
    collection = Collection.objects.get(contract_address=contract_address)

    # Calculate the number of occurrences for each {name, value} combo
    trait_type_map = {}

    for nft in collection.nfts.all().values("id", "raw_metadata__metadata__attributes"):
        attributes_values = nft["raw_metadata__metadata__attributes"]

        if attributes_values is not None:
            for attribute in attributes_values:
                name = attribute.get("trait_type")  # e.g Hat
                value = attribute.get("value")  # e.g Army Hat

                key = name
                if not name:
                    key = value

                if key in trait_type_map:
                    attribute_type = trait_type_map[key]
                    if value in attribute_type:
                        trait_type_map[key][value] += 1
                    else:
                        trait_type_map[key][value] = 1
                else:
                    trait_type_map[key] = {value: 1}

    logging.info(msg=f"Created attribute trait map for {contract_address}")

    # Here we create a CollectionAttribute for each of the Trait Counts
    # i.e. there are 1993 NFTs with 7 traits, 5232 NFTs with 6 traits etc.
    nft_trait_count_map = {}
    for nft_trait_count in collection.nfts.all().values_list("trait_count", flat=True):
        if nft_trait_count in nft_trait_count_map:
            nft_trait_count_map[nft_trait_count] += 1
        else:
            nft_trait_count_map[nft_trait_count] = 1

    CollectionAttribute.objects.bulk_create(
        [
            CollectionAttribute(
                collection=collection,
                name="Trait Count",
                value=nft_trait_count,  # e.g. 7 - meaning 7 traits
                occurrences=nft_trait_count_map[
                    nft_trait_count
                ],  # e.g. 1883 occurrences of 7 traits
            )
            for nft_trait_count in nft_trait_count_map.keys()
        ]
    )

    logging.info(
        msg=f"Bulk-created collection attributes for trait counts for {contract_address}"
    )

    # Save the number of NFTs for each trait and value
    collection_attributes_for_update = []
    for trait_name in trait_type_map.keys():
        if trait_name:
            trait_types = trait_type_map[trait_name]
            for trait_value in trait_types.keys():
                if trait_value:
                    trait_type_count = trait_types[trait_value]
                    collection_attribute = CollectionAttribute.objects.get(
                        collection=collection, name=trait_name, value=trait_value
                    )
                    collection_attribute.occurrences = trait_type_count
                    collection_attributes_for_update.append(collection_attribute)

    CollectionAttribute.objects.bulk_update(
        collection_attributes_for_update, ["occurrences"], batch_size=100
    )
    logging.info(
        msg=f"Updated collection attributes with occurrence counts for {contract_address}"
    )

    # Calculate rarity
    """
    [Rarity Score for a Trait Value] =
    1 / ([Number of Items with that Trait Value] / [Total Number of Items in Collection])
    """
    collection_attributes = CollectionAttribute.objects.filter(
        collection=collection, name="Trait Count"
    )
    collection_attributes_count = collection_attributes.count()

    nfts_for_update = []
    NFT.objects.filter(collection=collection)
    for nft in collection.nfts.all():
        # fetch all traits for NFT
        total_score = 0
        metadata = nft.raw_metadata["metadata"]
        attributes_values = metadata.get("attributes")
        if attributes_values:

            for attribute in attributes_values:
                name = attribute.get("trait_type", None)  # e.g Hat
                value = attribute.get("value", None)  # e.g Army Hat

                if name and value:
                    # Number of Items with that Trait Value
                    trait_sum = trait_type_map[name][value]
                    rarity_score = 1 / (trait_sum / collection.supply)
                    # TODO we could store rarity score on the metadata in case wanting to render it in the future
                    total_score += rarity_score
                else:
                    logging.error(
                        msg=f"NFT attribute data error in contract {contract_address} for NFT ID {nft.id}"
                    )

            # Add the NFT Trait Count Rarity score
            # The formula for the attribute score comes from rarity tools v1
            occurrences = nft_trait_count_map[nft.trait_count]
            attribute_score = (
                collection_attributes_count * 2 / (occurrences / collection.supply)
            )

            nft.rarity_score = total_score + attribute_score
            nfts_for_update.append(nft)

    NFT.objects.bulk_update(nfts_for_update, ["rarity_score"], batch_size=100)

    logging.info(msg=f"Saved NFT rarity scores for collection {contract_address}")

    # Rank NFTs
    nfts_for_update = []
    for index, nft in enumerate(collection.nfts.all().order_by("-rarity_score")):
        nft.rank = index + 1
        nfts_for_update.append(nft)

    NFT.objects.bulk_update(nfts_for_update, ["rank"], batch_size=100)
    logging.info(msg=f"Ranked NFTs for collection {contract_address}")

    connection.close()


@app.task(name="fetch_nfts")
def fetch_nfts(contract_address):
    collection = Collection.objects.get(contract_address=contract_address)
    logging.info(msg=f"Starting to fetch NFTs for contract: {contract_address}")
    alchemy_client = get_alchemy_client()

    # Clear out NFTs
    collection.nfts.all().delete()

    nfts = []

    has_next_page = True
    page_token = None
    while has_next_page:
        data = alchemy_client.get_nfts_for_collection(
            contract_address, start_token=page_token
        )
        APICallRecordLog.objects.create(
            client="alchemy", service="get_nfts_for_collection"
        )
        logging_service.log(
            {
                "Event": "Fetch NFTs for Collection",
                "Service": "Alchemy",
                "Collection_ID": collection.id,
                "Contract_Address": contract_address,
            }
        )
        nft_objs = []
        for nft in data["nfts"]:
            metadata = nft.get("metadata")
            if metadata is None or isinstance(metadata, Mapping) is False:
                logging.warning(
                    msg=f"NFT is missing in Alchemy collection response data for contract: "
                    f"{contract_address} and nft: {nft}"
                )
            else:
                attributes = metadata.get("attributes")

                if not attributes:
                    trait_count = 0
                else:
                    trait_count = len(attributes)

                token_id_str = nft.get("id").get("tokenId")
                if isinstance(token_id_str, str):
                    token_id = int(token_id_str, base=16)
                else:
                    token_id = token_id_str

                media = nft.get("media")
                image_url = None

                if media and len(media) > 0:
                    # print(f"NFT {nft.id} from collection {collection.id} media does not have media: {media}")
                    thumbnail = media[0].get("thumbnail")
                    gateway_url = media[0].get("gateway")  # IPFS

                    if thumbnail:
                        image_url = thumbnail
                    elif gateway_url:
                        if "https" in gateway_url:
                            image_url = gateway_url
                    else:
                        pass
                        # print(f"NFT {nft.id} media does not have thumbnail: {media}")

                if token_id:
                    nft_obj = NFT(
                        collection=collection,
                        name=nft.get("name"),
                        token_id=token_id,
                        image_url=image_url,
                        raw_metadata=nft,
                        trait_count=trait_count,
                    )
                    nft_objs.append(nft_obj)

        nfts += nft_objs

        page_token = data.get("nextToken")
        if not page_token or len(data["nfts"]) == 0:
            has_next_page = False

    logging.info(msg=f"Bulk creating NFTs for contract {contract_address}...")

    # Bulk create NFTs
    NFT.objects.bulk_create(nfts, batch_size=100)
    logging.info(msg=f"Created NFTs for contract {contract_address}")

    connection.close()


@app.task(name="create_nft_attributes")
def create_nft_attributes(contract_address):
    logging.info(msg=f"Creating CollectionAttributes for contract {contract_address}")
    collection = Collection.objects.get(contract_address=contract_address)

    # Clear out collection attributes
    collection.attributes.all().delete()

    # Create a map of all the attribute traits and values
    attribute_map = {}
    collection_attributes = collection.nfts.all().values(
        "id", "raw_metadata__metadata__attributes"
    )
    for a in collection_attributes:
        attributes = a["raw_metadata__metadata__attributes"]

        if not attributes:
            logging.error(
                msg=f"Bad metadata attributes for contract {contract_address} "
                f"collection attribute: {a['id']}"
            )
        else:
            for attribute in attributes:
                if attribute and isinstance(attribute, Mapping):
                    name = attribute.get("trait_type")  # e.g Hat
                    value = attribute.get("value")  # e.g Army Hat

                    # E.g for VeeFriends an attribute won't have a trait type: { "value": "Sky" }
                    key = name
                    if not name:
                        key = value

                    if key in attribute_map:
                        attribute_map[key].append(value)
                    else:
                        attribute_map[key] = [value]

    collection_attributes_for_creation = []
    for name in attribute_map:
        for value in set(attribute_map[name]):
            if value:
                collection_attributes_for_creation.append(
                    CollectionAttribute(collection=collection, name=name, value=value)
                )

    CollectionAttribute.objects.bulk_create(
        collection_attributes_for_creation, batch_size=50
    )
    logging.info(msg=f"Created CollectionAttributes for contract {contract_address}")

    connection.close()


@app.task(name="link_nfts_to_transactions")
def link_nfts_to_transactions(contract_address):
    logging.info(
        msg=f"Started linking nfts to wallets for contract: {contract_address}"
    )
    collection = Collection.objects.get(contract_address=contract_address)
    transactions: QuerySet[Transaction] = Transaction.objects.filter(
        contract_address=contract_address, collection_only=False
    )

    transactions_to_update = []
    # Assign NFT based on token_id of transaction
    for transaction_obj in transactions:
        nft = NFT.objects.filter(
            collection=collection, token_id=transaction_obj.token_id
        ).first()
        transaction_obj.nft = nft
        transactions_to_update.append(transaction_obj)

    Transaction.objects.bulk_update(transactions_to_update, ["nft"], batch_size=100)

    logging.info(
        msg=f"Finished linking nfts to transactions for contract: {contract_address}"
    )

    connection.close()

    return "Done"


@app.task(name="link_nfts_to_wallets")
def link_nfts_to_wallets(contract_address):
    logging.info(
        msg=f"Started linking nfts to wallets for contract: {contract_address}"
    )
    collection = Collection.objects.get(contract_address=contract_address)
    wallet_nfts = WalletNFT.objects.filter(
        nft_raw_data__contract_address=contract_address
    )

    wallet_nfts_to_update = []

    for wallet_nft in wallet_nfts:
        token_id = wallet_nft.nft_raw_data.get("token_id", None)
        if not token_id:
            logging.warning(
                msg=f"WalletNFT has missing token_id in nft_raw_data for walletnft: {wallet_nft.id}"
            )
        else:
            wallet_nft.nft = NFT.objects.filter(
                collection=collection, token_id=token_id
            ).first()
            wallet_nfts_to_update.append(wallet_nft)

    WalletNFT.objects.bulk_update(wallet_nfts_to_update, ["nft"], batch_size=100)

    logging.info(
        msg=f"Finished linking nfts to wallets for contract: {contract_address}"
    )

    connection.close()

    return "Done"


def calculate_collection_rarity_task(contract_address):
    # Step 1 - get NFTs for the contract - saves them in the DB
    step1 = fetch_nfts.si(contract_address)

    # Step 2 - Create NFT traits and attributes
    step2 = create_nft_attributes.si(contract_address)

    # Step 3 - Rank NFTs using traits and attributes
    step3 = rank_nfts.si(contract_address)

    # Step 4 - Link NFTs to transactions
    step4 = link_nfts_to_transactions.si(contract_address)

    # Step 5 - Link NFTs to wallets
    step5 = link_nfts_to_wallets.si(contract_address)

    workflow = chain(step1, step2, step3, step4, step5)
    result = workflow.delay()
    return result


@app.task(name="fetch_collections_transfers")
def fetch_collections_transfers():
    """
    This task allows us to fetch thousands of transactions across collections but doesn't provide
    the value (eth) of the transaction.
    """
    contract_addresses = list(
        Collection.objects.filter(released=True)
        .order_by("id")
        .values_list("contract_address", flat=True)
    )

    def chunker(seq, size):
        return (seq[pos : pos + size] for pos in range(0, len(seq), size))  # noqa

    def get_transaction_type(t):
        transfer_type = t.get("transferType")

        type_mint = "TRANSFER_TYPE_MINT"
        type_burn = "TRANSFER_TYPE_BURN"
        # type_regular = "TRANSFER_TYPE_REGULAR"

        if transfer_type == type_mint:
            return "mint"

        elif transfer_type == type_burn:
            return "burn"

        return "transfer"

    for group in chunker(contract_addresses, 1):
        offset = 0
        has_next_page = True
        transactions = []

        last_block_timestamp = None
        last_eth_block: EthBlock = (
            EthBlock.objects.filter(contract_address=group[0])
            .order_by("-last_block")
            .first()
        )
        if last_eth_block:
            last_block_timestamp = last_eth_block.timestamp

        last_fetched_block_number = None
        last_fetched_block_timestamp = None

        while has_next_page:
            time.sleep(0.5)
            contract_address = group[0]
            data = mnemonic_client.get_collection_transfers(
                contract_address,
                limit=500,
                offset=offset,
                timestamp__gt=last_block_timestamp,
            )
            APICallRecordLog.objects.create(
                client="mnemonic", service="get_collection_transfers"
            )
            logging_service.log(
                {
                    "Event": "Fetch Collection Transfers",
                    "Service": "Mnemonic",
                    "Contract_Address": contract_address,
                }
            )

            error = data.get("error")

            if error:
                logging.error(
                    msg=f"Failed to fetch sales for contract addresses: {group}: {error}"
                )
                return

            transfers = data.get("nftTransfers")
            if not transfers:
                has_next_page = False

            elif transfers:
                result_count = len(transfers)
                print(f"Page offset: {offset}. Result count: {result_count}")

                if result_count == 500:
                    offset += 500
                else:
                    has_next_page = False

                for transfer in transfers:
                    transfer_type = get_transaction_type(transfer)

                    contract_address = transfer.get("contractAddress")
                    block_number = transfer.get("blockchainEvent").get("blockNumber")
                    token_id = transfer.get("tokenId")
                    quantity = transfer.get("quantity")
                    transaction_hash = transfer.get("blockchainEvent").get("txHash")
                    transaction_timestamp = parser.parse(
                        transfer.get("blockchainEvent").get("blockTimestamp")
                    )

                    sender = transfer.get("sender")
                    sender_address = sender.get("address")

                    recipient = transfer.get("recipient")
                    receiver_address = recipient.get("address")

                    recipient_paid = transfer.get("recipientPaid")
                    price_eth = None
                    price_usd = None
                    if recipient_paid:
                        price_eth = recipient_paid.get("totalEth")
                        price_usd = recipient_paid.get("totalUsd")

                    if contract_address and token_id:
                        # These transactions are to display in the sales/transfers tab
                        # so they don't need a wallet associated with it
                        tx = Transaction(
                            nft=(
                                NFT.objects.filter(
                                    collection__contract_address=contract_address,
                                    token_id=token_id,
                                ).first()
                            ),
                            transaction_type=transfer_type,
                            transfer_from=sender_address,
                            transfer_to=receiver_address,
                            contract_address=contract_address,
                            token_id=token_id,
                            quantity=int(quantity),
                            transaction_hash=transaction_hash,
                            block_number=block_number,
                            transaction_date=transaction_timestamp,
                            raw_transaction_data=transfer,
                            collection_only=True,
                            price_eth=price_eth,
                            price_usd=price_usd,
                        )
                        transactions.append(tx)
                    last_fetched_block_number = block_number
                    last_fetched_block_timestamp = transaction_timestamp

                EthBlock.objects.create(
                    last_block=last_fetched_block_number,
                    timestamp=last_fetched_block_timestamp,
                    contract_address=group[0],
                )

        Transaction.objects.bulk_create(transactions, batch_size=100)

    connection.close()
    return "Done"


@app.task(name="collection_callback")
def collection_callback(contract_address):
    return f"Completed tasks for collection: {contract_address}"


@app.task(name="fetch_collection_owners_history")
def fetch_collection_owners_history():
    logging.info(msg="Fetching collection owners history")
    collection_metrics: QuerySet[CollectionMetrics] = CollectionMetrics.objects.filter(
        collection__released=True
    )
    collection_metrics_to_update = []
    for collection_metric in collection_metrics:
        try:
            collection = collection_metric.collection
            results = mnemonic_client.get_historical_collection_owners(
                collection.contract_address
            )
            APICallRecordLog.objects.create(
                client="mnemonic", service="collection_owners_history"
            )
            logging_service.log(
                {
                    "Event": "Fetch Collection Owners History",
                    "Service": "Mnemonic",
                    "Collection_ID": collection.id,
                    "Collection_Name": collection.name,
                    "Contract_Address": collection.contract_address,
                }
            )

            collection_metric.owners_history = results.get("dataPoints")
            collection_metrics_to_update.append(collection_metric)
            time.sleep(0.3)
        except Exception:
            pass

    CollectionMetrics.objects.bulk_update(
        collection_metrics_to_update, ["owners_history"], batch_size=100
    )
    logging.info(msg="Finished fetching collection owners history")
    connection.close()


@app.task(name="fetch_collection_price_history")
def fetch_collection_price_history():
    logging.info(msg="Fetching collection prices history")
    collection_metrics: QuerySet[CollectionMetrics] = CollectionMetrics.objects.filter(
        collection__released=True
    )
    collection_metrics_to_update = []
    for collection_metric in collection_metrics:
        try:
            collection = collection_metric.collection
            results = mnemonic_client.get_historical_price_history(
                collection.contract_address
            )
            APICallRecordLog.objects.create(
                client="mnemonic", service="collection_price_history"
            )
            logging_service.log(
                {
                    "Event": "Fetch Collection Price History",
                    "Service": "Mnemonic",
                    "Collection_ID": collection.id,
                    "Collection_Name": collection.name,
                    "Contract_Address": collection.contract_address,
                }
            )

            collection_metric.price_history = results.get("dataPoints")
            collection_metrics_to_update.append(collection_metric)
            time.sleep(0.3)
        except Exception:
            pass

    CollectionMetrics.objects.bulk_update(
        collection_metrics_to_update, ["price_history"], batch_size=100
    )
    logging.info(msg="Finished fetching collection prices history")
    connection.close()


@app.task(name="fetch_trending_collections")
def fetch_trending_collections():
    logging.info(msg="Fetching trending collections")

    trending_by_sales = mnemonic_client.get_trending_collections(
        TrendingBy.sales, limit=20, offset=0
    )
    trending_by_volume = mnemonic_client.get_trending_collections(
        TrendingBy.volume, limit=20, offset=0
    )
    trending_by_price = mnemonic_client.get_trending_collections(
        TrendingBy.price, limit=20, offset=0
    )

    # Loop through data and attach a serialized collection to each item in the list
    data = [trending_by_sales, trending_by_volume, trending_by_price]
    for trending_data in data:
        for result in trending_data["collections"]:
            collection = Collection.objects.filter(
                contract_address=result["contractAddress"]
            ).first()
            if collection:
                thumbnail = None
                if collection.thumbnail:
                    thumbnail = collection.thumbnail.url
                try:
                    floor_price = collection.collectionmetrics.current_floor_price
                except CollectionMetrics.DoesNotExist:
                    floor_price = None
                result["collection"] = {
                    "name": collection.name,
                    "thumbnail": thumbnail,
                    "floor_price": floor_price,
                }

    TrendingCollections.objects.create(
        trending_by_volume=trending_by_volume,
        trending_by_sales=trending_by_sales,
        trending_by_price=trending_by_price,
    )

    logging.info(msg="Finished fetching trending collections")

    connection.close()

    return "Created"


@app.task(name="fetch_eth_price")
def fetch_eth_price():
    cg = CoinGeckoAPI()
    data = cg.get_price(ids="ethereum", vs_currencies="usd")
    eth = data.get("ethereum")
    if eth:
        price = eth.get("usd")
        EthPrice.objects.create(date=datetime.date.today(), value=price)
    connection.close()


def fetch_eth_price_history():
    import csv

    prices = []

    with open("data/ETH-USD.csv") as f:
        reader = csv.DictReader(f)

        for row in reader:
            date = row["Date"]
            price = row["Close"]

            prices.append(EthPrice(date=date, value=price))

    EthPrice.objects.bulk_create(prices, batch_size=100)
    connection.close()
