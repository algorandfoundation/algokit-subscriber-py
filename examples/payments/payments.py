import logging

from algokit_utils import AlgorandClient

import algokit_subscriber as sub

# configure simple logging for algokit_subscriber
logger = logging.getLogger("algokit_subscriber")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

algorand = AlgorandClient.mainnet()


subscriber = sub.AlgorandSubscriber(
    # algod is used to get the latest transactions once the subscriber has caught up to the network
    algod_client=algorand.client.algod,
    config=sub.AlgorandSubscriberConfig(
        # Filters are defined as a list of named filters.
        # A filter name can be used multiple times to create an OR filter.
        filters=[
            sub.SubscriberConfigFilter(
                name="pay txns",
                filter=sub.TransactionFilter(
                    # Match payment transactions
                    type="pay",
                    # We only want transactions that transferred at least 1 ALGO
                    min_amount=int(1e6),
                ),
            ),
        ],
        # Once we are caught up, always wait until the next block is available
        # and process it immediately once available
        wait_for_block_when_at_tip=True,
        # In this example, we are starting at round 41651683
        watermark_persistence=sub.in_memory_watermark(41651683),
        # there are a lot of pay transactions, so limit to batches of 1000 at a time
        max_indexer_rounds_to_sync=1000,
        # Use indexer to get historical transactions. Indexer is not required
        # to use the subscriber, but it can be used to quickly get batch
        # transactions via indexer API queries
        sync_behaviour="catchup-with-indexer",
    ),
    # indexer is OPTIONALLY used to get historical transactions. We only need
    # it here because we're using the 'sync_behaviour' of 'catchup-with-indexer'
    indexer_client=algorand.client.indexer,
)


def print_payment(transaction: sub.SubscribedTransaction, filter_name: str) -> None:
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
    pay = transaction.payment_transaction
    if pay is None:
        return
    print(f"{filter_name}: {transaction.sender} sent {pay.receiver} {pay.amount * 1e-6} ALGO")


# Attach our callback to the 'pay txns' filter
subscriber.on("pay txns", print_payment)
# Start the subscriber
subscriber.start()
