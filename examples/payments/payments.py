from algokit_subscriber.subscriber import AlgorandSubscriber
from algokit_subscriber.types.subscription import SubscribedTransaction
from algokit_utils.beta.algorand_client import AlgorandClient

algorand = AlgorandClient.main_net()

# The watermark is used to track how far the subscriber has processed transactions
# In this example, we are starting at round 41651683
watermark = 41651683


def get_watermark() -> int:
    return watermark


def set_watermark(new_watermark: int) -> None:
    global watermark  # noqa: PLW0603
    watermark = new_watermark


subscriber = AlgorandSubscriber(
    # algod is used to get the latest transactions once the subscriber has caught up to the network
    algod_client=algorand.client.algod,
    config={
        # We can define one or more filters for the subscriber to listen for
        "filters": [
            {
                "name": "pay txns",
                "filter": {
                    # Match payment transactions
                    "type": "pay",
                    # We only want transactions that transferred at least 1 ALGO
                    "min_amount": int(1e6),
                },
            }
        ],
        # Once we are caught up, always wait until the next block is available and process it immediately once available
        "wait_for_block_when_at_tip": True,
        # The watermark persistence functions are used to get and set the watermark
        "watermark_persistence": {"get": get_watermark, "set": set_watermark},
        # Use indexer to get historical transactions
        # Indexer is not required to use the subscriber, but it can be used to quickly get batch transactions via indexer API queries
        "sync_behaviour": "catchup-with-indexer",
    },
    # indexer is OPTIONALLY used to get historical transactions. We only need it here because we're using the 'sync_behaviour' of 'catchup-with-indexer'
    indexer_client=algorand.client.indexer,
)


def print_payment(transaction: SubscribedTransaction, filter_name: str) -> None:
    """
    This is an EventListener callback. It will be called for every transaction that matches the filter.

    Every EventListener callback will receive two arguments:
    * The transaction data
    * The filter name (from the 'filters' list) that the transaction matched

    Here we are only using this EventListener callback for one filter, but if we had multiple filters we could use the filter name to determine which filter the transaction matched.
    """
    pay = transaction["payment-transaction"]
    print(
        f"{filter_name}: {transaction['sender']} sent {pay['receiver']} {pay['amount'] * 1e-6} ALGO"
    )


# Attach our callback to the 'pay txns' filter
subscriber.on("pay txns", print_payment)
# Start the subscriber
subscriber.start()
