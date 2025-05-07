import base64
import json
import random

from algokit_subscriber.subscriber import AlgorandSubscriber
from algokit_subscriber.types.subscription import SubscribedTransaction
from algokit_utils.beta.algorand_client import AlgorandClient
from algokit_utils.beta.composer import PayParams

algorand = AlgorandClient.default_local_net()


dispenser = algorand.account.localnet_dispenser()
sender = algorand.account.random()

# Fund the sender
algorand.send.payment(PayParams(sender=dispenser.address, receiver=sender.address, amount=1_000_000))

# Send a governance commitment message
algorand.send.payment(
    PayParams(
        sender=sender.address,
        receiver=sender.address,
        amount=0,
        # Commit a random amount of ALGO
        note=f'af/gov1:j{{"com":{random.randint(1_000_000, 100_000_000)}}}'.encode(),
    )
)

# Send an unrelated message
algorand.send.payment(
    PayParams(
        sender=sender.address,
        receiver=sender.address,
        amount=0,
        note=b"Some random txn",
    )
)

# Every subscriber instance uses a watermark to track what block it processed last.
# In this example we are using a variable to track the watermark

watermark = 0


# To implement a watermark in the subscriber, we must define a get and set function
def get_watermark() -> int:
    """
    Get the current watermark value
    """
    return watermark


def set_watermark(new_watermark: int) -> None:
    """
    Set our watermark variable to the new watermark from the subscriber
    """
    global watermark  # noqa: PLW0603
    watermark = new_watermark


subscriber = AlgorandSubscriber(
    algod_client=algorand.client.algod,
    indexer_client=algorand.client.indexer,
    config={
        "filters": [
            {
                "name": "Governance",
                "filter": {
                    "type": "pay",
                    "note_prefix": "af/gov1:j",
                },
            },
        ],
        # Instead of always waiting for the next block, just poll for new blocks every 10 seconds
        "wait_for_block_when_at_tip": False,
        "frequency_in_seconds": 10,
        # The watermark persistence functions are used to get and set the watermark
        "watermark_persistence": {"get": get_watermark, "set": set_watermark},
        # Indexer has the ability to filter transactions server-side, resulting in less API calls
        # This is only useful if we have a very specific query, such as a note prefix
        "sync_behaviour": "catchup-with-indexer",
    },
)


def print_transfer(transaction: SubscribedTransaction, _: str) -> None:
    """
    This is an EventListener callback. We use the .on function below to attach this callback to specific events.

    Every EventListener callback will receive two arguments:
    * The transaction data
    * The filter name (from the 'filters' list) that the transaction matched
    """
    json_data = base64.b64decode(transaction["note"]).decode().split(":j")[1].replace("”", '"').replace("“", '"')

    amount = json.loads(json_data)["com"] * 1e-6

    print(f"Transaction {transaction['sender']} committed {amount} ALGO on round {transaction['confirmed-round']} in transaction {transaction['id']}")


# Attach the callback to the events we are interested in
subscriber.on("Governance", print_transfer)

# Start the subscriber
subscriber.start()
