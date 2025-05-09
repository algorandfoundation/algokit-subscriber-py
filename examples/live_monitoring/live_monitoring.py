from typing import TYPE_CHECKING

from algokit_utils.beta.algorand_client import AlgorandClient

from algokit_subscriber.subscriber import AlgorandSubscriber
from algokit_subscriber.types.subscription import SubscribedTransaction

if TYPE_CHECKING:
    from algokit_subscriber.types.indexer import (
        AssetTransferTransactionResult,
        PaymentTransactionResult,
    )

algorand = AlgorandClient.main_net()

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
    config={
        "filters": [
            {
                "name": "USDC",
                # Only match non-zero USDC transfers
                "filter": {
                    "type": "axfer",
                    "asset_id": 31566704,  # mainnet usdc
                    "min_amount": 1,
                },
            },
            {
                "name": "ALGO",
                # Only match non-zero ALGO transfers
                "filter": {
                    "type": "pay",
                    "min_amount": 1,
                },
            },
        ],
        # Once we are caught up, always wait until the next block is available and process it immediately once available
        "wait_for_block_when_at_tip": True,
        # The watermark persistence functions are used to get and set the watermark
        "watermark_persistence": {"get": get_watermark, "set": set_watermark},
        # Skip the sync process and immediately get the latest block in the network
        "sync_behaviour": "skip-sync-newest",
        # Max rounds to sync defines how many rounds to lookback when first starting the subscriber
        # If syncing via a non-archival node, this could be up to 1000 rounds back
        # In this example we want to immediately start processing the latest block without looking back
        "max_rounds_to_sync": 1,
    },
)


def print_transfer(transaction: SubscribedTransaction, filter_name: str) -> None:
    """
    This is an EventListener callback. We use the .on function below to attach this callback to specific events.

    Every EventListener callback will receive two arguments:
    * The transaction data
    * The filter name (from the 'filters' list) that the transaction matched
    """
    details: PaymentTransactionResult | AssetTransferTransactionResult
    if filter_name == "USDC":
        details = transaction["asset-transfer-transaction"]
    elif filter_name == "ALGO":
        details = transaction["payment-transaction"]

    print(
        f"{transaction['sender']} sent {details['receiver']} {details['amount'] * 1e-6} {filter_name} in transaction {transaction['id']}"
    )


# Attach the callback to the events we are interested in
subscriber.on("ALGO", print_transfer)
subscriber.on("USDC", print_transfer)

# Start the subscriber
subscriber.start()
