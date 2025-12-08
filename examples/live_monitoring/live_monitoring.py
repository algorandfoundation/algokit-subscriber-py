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
        filters=[
            # Only match non-zero USDC transfers
            sub.SubscriberConfigFilter(
                name="USDC",
                type="axfer",
                asset_id=31566704,  # mainnet usdc
                min_amount=1,
            ),
            # Only match non-zero ALGO transfers
            sub.SubscriberConfigFilter(
                name="ALGO",
                type="pay",
                min_amount=1,
            ),
        ],
        # Once we are caught up, always wait until the next block is available
        # and process it immediately once available
        wait_for_block_when_at_tip=True,
        # Every subscriber instance uses a watermark to track what block it processed last.
        # In this example we are using a simple in memory watermark
        watermark_persistence=sub.in_memory_watermark(),
        # Skip the sync process and immediately get the latest block in the network
        sync_behaviour="skip-sync-newest",
        # Max rounds to sync defines how many rounds to lookback when first
        # starting the subscriber. If syncing via a non-archival node, this
        # could be up to 1000 rounds back. In this example we want to
        # immediately start processing the latest block without looking back
        max_rounds_to_sync=1,
    ),
)


def print_transfer(transaction: sub.SubscribedTransaction, filter_name: str) -> None:
    """
    This is an EventListener callback. We use the .on function below to attach
    this callback to specific events.

    Every EventListener callback will receive two arguments:
    * The transaction data
    * The filter name (from the 'filters' list) that the transaction matched
    """
    if filter_name == "USDC" and (axfer := transaction.asset_transfer_transaction):
        receiver = axfer.receiver
        amount = axfer.amount
    elif filter_name == "ALGO" and (pay := transaction.payment_transaction):
        receiver = pay.receiver
        amount = pay.amount
    else:
        return

    print(
        f"{transaction.sender} sent {receiver} {amount * 1e-6} {filter_name} "
        f"in transaction {transaction.id_}"
    )


# Attach the callback to the events we are interested in
subscriber.on("ALGO", print_transfer)
subscriber.on("USDC", print_transfer)

# Start the subscriber
subscriber.start()
