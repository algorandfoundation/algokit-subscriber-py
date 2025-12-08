import logging

from algokit_utils import AlgorandClient

import algokit_subscriber as sub

# configure simple logging for algokit_subscriber
logger = logging.getLogger("algokit_subscriber")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

algorand = AlgorandClient.mainnet()


subscriber = sub.AlgorandSubscriber(
    algod_client=algorand.client.algod,
    config=sub.AlgorandSubscriberConfig(
        # Filters are defined as a list of named filters.
        # A filter name can be used multiple times to create an OR filter.
        filters=[
            # Only match asset transfers of USDC that are more than 1 USDC
            sub.SubscriberConfigFilter(
                name="usdc",
                type="axfer",
                asset_id=31566704,  # mainnet usdc
                min_amount=1_000_000,
            ),
        ],
        # Once we are caught up, always wait until the next block is available
        # and process it immediately once available
        wait_for_block_when_at_tip=True,
        # The watermark is used to track how far the subscriber has processed transactions
        # In this example, we are starting at round 41651683
        watermark_persistence=sub.in_memory_watermark(41651683),
        # Skip the sync process and immediately get the latest block in the network
        sync_behaviour="skip-sync-newest",
    ),
)


def print_usdc(transaction: sub.SubscribedTransaction, filter_name: str) -> None:
    """
    This is an EventListener callback. It will be called for every transaction
    that matches the filter.

    Every EventListener callback will receive two arguments:
    * The transaction data
    * The filter name (from the 'filters' list) that the transaction matched

    Here we are only using this EventListener callback for one filter, but if
    we had multiple filters we could use the filter name to determine which
    filter the transaction matched.
    """
    axfer = transaction.asset_transfer_transaction
    if axfer is None:
        return
    print(f"{filter_name}: {transaction.sender} sent {axfer.receiver} {axfer.amount * 1e-6} USDC")


subscriber.on("usdc", print_usdc)
subscriber.start()
