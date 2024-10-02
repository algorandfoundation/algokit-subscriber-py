from algokit_subscriber.subscriber import AlgorandSubscriber
from algokit_subscriber.types.subscription import SubscribedTransaction
from algokit_utils.beta.algorand_client import AlgorandClient

algorand = AlgorandClient.main_net()

# The watermark is used to track how far the subscriber has processed transactions
# In this example, we are starting at round 41651683
watermark = 0


def get_watermark() -> int:
    return watermark


def set_watermark(new_watermark: int) -> None:
    global watermark  # noqa: PLW0603
    watermark = new_watermark


subscriber = AlgorandSubscriber(
    algod_client=algorand.client.algod,
    config={
        "filters": [
            {
                # The name of the filter
                "name": "usdc",
                # Only match asset transfers of USDC that are more than 1 USDC
                "filter": {
                    "type": "axfer",
                    "asset_id": 31566704,  # mainnet usdc
                    "min_amount": 1_000_000,
                },
            }
        ],
        # Once we are caught up, always wait until the next block is available and process it immediately once available
        "wait_for_block_when_at_tip": True,
        # The watermark persistence functions are used to get and set the watermark
        "watermark_persistence": {"get": get_watermark, "set": set_watermark},
        # Skip the sync process and immediately get the latest block in the network
        "sync_behaviour": "skip-sync-newest",
    },
)


def print_usdc(transaction: SubscribedTransaction, filter_name: str) -> None:
    """
    This is an EventListener callback. It will be called for every transaction that matches the filter.

    Every EventListener callback will receive two arguments:
    * The transaction data
    * The filter name (from the 'filters' list) that the transaction matched

    Here we are only using this EventListener callback for one filter, but if we had multiple filters we could use the filter name to determine which filter the transaction matched.
    """
    axfer = transaction["asset-transfer-transaction"]
    print(
        f"{filter_name}: {transaction['sender']} sent {axfer['receiver']} {axfer['amount'] * 1e-6} USDC"
    )


subscriber.on("usdc", print_usdc)
subscriber.start()
