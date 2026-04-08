import json
import logging
import random

from algokit_utils import AlgoAmount, AlgorandClient, PaymentParams

import algokit_subscriber as sub

# configure simple logging for algokit_subscriber
logger = logging.getLogger("algokit_subscriber")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

algorand = AlgorandClient.default_localnet()

dispenser = algorand.account.localnet_dispenser()
sender = algorand.account.random()

# Fund the sender
algorand.send.payment(
    PaymentParams(
        sender=dispenser.addr,
        receiver=sender.addr,
        amount=AlgoAmount(micro_algo=1_000_000),
    )
)

# Send a governance commitment message
algorand.send.payment(
    PaymentParams(
        sender=sender.addr,
        receiver=sender.addr,
        amount=AlgoAmount(micro_algo=0),
        # Commit a random amount of ALGO
        note=f'af/gov1:j{{"com":{random.randint(1_000_000, 100_000_000)}}}'.encode(),
    )
)

# Send an unrelated message
algorand.send.payment(
    PaymentParams(
        sender=sender.addr,
        receiver=sender.addr,
        amount=AlgoAmount(micro_algo=0),
        note=b"Some random txn",
    )
)

subscriber = sub.AlgorandSubscriber(
    algod_client=algorand.client.algod,
    indexer_client=algorand.client.indexer,
    config=sub.AlgorandSubscriberConfig(
        filters=[
            sub.SubscriberConfigFilter(
                name="Governance",
                filter=sub.TransactionFilter(
                    type="pay",
                    note_prefix="af/gov1:j",
                ),
            ),
        ],
        # Instead of always waiting for the next block, just poll for new blocks every 10 seconds
        wait_for_block_when_at_tip=False,
        frequency_in_seconds=10,
        # Every subscriber instance uses a watermark to track what block it processed last.
        # In this example we are using a simple in memory watermark
        watermark_persistence=sub.in_memory_watermark(),
        # Indexer has the ability to filter transactions server-side, resulting in less API calls
        # This is only useful if we have a very specific query, such as a note prefix
        sync_behaviour="catchup-with-indexer",
    ),
)


def print_transfer(transaction: sub.SubscribedTransaction, _: str) -> None:
    """
    This is an EventListener callback. We use the .on function below to attach
    this callback to specific events.

    Every EventListener callback will receive two arguments:
    * The transaction data
    * The filter name (from the 'filters' list) that the transaction matched
    """
    if transaction.note is None:
        return
    json_data = transaction.note.decode().split(":j")[1].replace(""", '"').replace(""", '"')

    amount = json.loads(json_data)["com"] * 1e-6

    print(
        f"Transaction {transaction.sender} committed {amount} ALGO "
        f"on round {transaction.confirmed_round} in transaction {transaction.id_}"
    )


def print_round(result: sub.TransactionSubscriptionResult, _: str) -> None:
    round_from, round_to = result.synced_round_range
    print(f"Synced rounds {round_from} to {round_to}")


subscriber.on_poll(print_round)
# Attach the callback to the events we are interested in
subscriber.on("Governance", print_transfer)

# Start the subscriber
subscriber.start()
