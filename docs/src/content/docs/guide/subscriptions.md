---
title: get_subscribed_transactions
description: Guide to using get_subscribed_transactions for single-poll blockchain subscription.
---

# `get_subscribed_transactions`

`get_subscribed_transactions` is the core building block at the centre of this library. It's a simple, but flexible mechanism that allows you to enact a single subscription "poll" of the Algorand blockchain.

This is a lower level building block, you likely don't want to use it directly, but instead use the [`AlgorandSubscriber` class](../subscriber/).

You can use this method to orchestrate everything from an index of all relevant data from the start of the chain through to simply subscribing to relevant transactions as they emerge at the tip of the chain. It allows you to have reliable at least once delivery even if your code has outages through the use of watermarking.

```python
import algokit_subscriber as sub

result = sub.get_subscribed_transactions(
    subscription=sub.TransactionSubscriptionParams(
        filters=[sub.TransactionFilter(name="my-filter", sender="ABC...")],
        watermark=0,
        sync_behaviour="skip-sync-newest",
    ),
    algod=algod_client,
    indexer=indexer_client,  # optional, only needed for catchup-with-indexer
)
```

## TransactionSubscriptionParams

Specifying a subscription requires passing in a [`TransactionSubscriptionParams`](../../api/algokit_subscriber/) object, which configures the behaviour. See the full API reference for details on all available fields.

Key fields include:

- `filters` - A list of [`TransactionFilter`](../../api/algokit_subscriber/) definitions. A filter name can be used multiple times to create an OR filter.
- `watermark` - The current round watermark that transactions have previously been synced to
- `sync_behaviour` - How to handle when the chain tip is more than `max_rounds_to_sync` past `watermark`
- `arc28_events` - Optional dict of [`Arc28EventGroup`](../../api/algokit_subscriber/) definitions for ARC-28 event processing
- `max_rounds_to_sync` - Maximum rounds to sync per poll (default: 500)
- `max_indexer_rounds_to_sync` - Maximum rounds to sync from indexer when using `catchup-with-indexer`

## TransactionFilter

The `filters` parameter allows you to specify a set of filters to return a subset of transactions you are interested in. See [`TransactionFilter`](../../api/algokit_subscriber/) for the full API reference.

Each filter you provide applies an AND logic between the specified fields, e.g.:

```python
import algokit_subscriber as sub

sub.TransactionFilter(
    name="my-filter",
    type="axfer",
    sender="ABC...",
)
```

Will return transactions that are `axfer` type AND have a sender of `"ABC..."`.

You can supply multiple named filters as a list. This gives you the ability to detect which filter got matched when a transaction is returned (via the `filters_matched` field). A filter name can be used multiple times to implement OR logic - transactions matching any filter with the same name will be returned.

## Arc28EventGroup

The `arc28_events` parameter allows you to define any ARC-28 events that may appear in subscribed transactions so they can either be subscribed to, or be processed and added to the resulting subscribed transaction object.

See:

- [`Arc28EventGroup`](../../api/algokit_subscriber/) - Group of ARC-28 event definitions
- [`Arc28Event`](../../api/algokit_subscriber/) - Individual event definition
- [`Arc28EventArg`](../../api/algokit_subscriber/) - Event argument definition

## TransactionSubscriptionResult

The result of calling `get_subscribed_transactions` is a [`TransactionSubscriptionResult`](../../api/algokit_subscriber/) which includes:

- `synced_round_range` - The round range that was synced from/to
- `current_round` - The current detected tip of the chain
- `starting_watermark` - The watermark value at the start of the poll
- `new_watermark` - The new watermark value to persist for the next poll
- `subscribed_transactions` - List of [`SubscribedTransaction`](../../api/algokit_subscriber/) that matched filters
- `block_metadata` - Optional list of [`BlockMetadata`](../../api/algokit_subscriber/) for retrieved blocks

## SubscribedTransaction

The common model used to expose a transaction that is returned from a subscription is [`SubscribedTransaction`](../../api/algokit_subscriber/).

This type is substantively based on the Indexer `Transaction` model format. While the indexer type is used, the subscriber itself doesn't have to use indexer - any transactions it retrieves from algod are transformed to this common model type.

Beyond the indexer type it has additional fields:

- `parent_transaction_id` - Reference to parent transaction for inner transactions
- `inner_txns` - Inner transactions (recursively) with the same extra fields
- `arc28_events` - List of [`EmittedArc28Event`](../../api/algokit_subscriber/) emitted from app calls
- `filters_matched` - Names of filters that matched this transaction
- `balance_changes` - List of [`BalanceChange`](../../api/algokit_subscriber/) in the transaction

## Examples

### Real-time notification at the tip of the chain, discarding stale records

```python
import algokit_subscriber as sub
from algokit_utils import AlgorandClient

algorand = AlgorandClient.testnet()

subscriber = sub.AlgorandSubscriber(
    config=sub.AlgorandSubscriberConfig(
        filters=[
            sub.SubscriberConfigFilter(
                name="filter1",
                sender="ER7AMZRPD5KDVFWTUUVOADSOWM4RQKEEV2EDYRVSA757UHXOIEKGMBQIVU",
            ),
        ],
        wait_for_block_when_at_tip=True,
        watermark_persistence=sub.in_memory_watermark(),
        sync_behaviour="skip-sync-newest",
        max_rounds_to_sync=100,
    ),
    algod_client=algorand.client.algod,
)


def notify_transactions(transaction: sub.SubscribedTransaction, _: str) -> None:
    print(f"New transaction from {transaction.sender}")


subscriber.on("filter1", notify_transactions)
subscriber.start()
```

### Real-time notification with at-least-once delivery

```python
import algokit_subscriber as sub
from algokit_utils import AlgorandClient

algorand = AlgorandClient.testnet()

subscriber = sub.AlgorandSubscriber(
    config=sub.AlgorandSubscriberConfig(
        filters=[
            sub.SubscriberConfigFilter(
                name="filter1",
                sender="ER7AMZRPD5KDVFWTUUVOADSOWM4RQKEEV2EDYRVSA757UHXOIEKGMBQIVU",
            ),
        ],
        wait_for_block_when_at_tip=True,
        watermark_persistence=sub.in_memory_watermark(),
        sync_behaviour="sync-oldest-start-now",
        max_rounds_to_sync=100,
    ),
    algod_client=algorand.client.algod,
)


def notify_transactions(transaction: sub.SubscribedTransaction, _: str) -> None:
    print(f"New transaction from {transaction.sender}")


subscriber.on("filter1", notify_transactions)
subscriber.start()
```

### Building a reliable cache index from the beginning of the chain

```python
import algokit_subscriber as sub
from algokit_utils import AlgorandClient

algorand = AlgorandClient.testnet()


def save_transactions(transactions: list[sub.SubscribedTransaction]) -> None:
    pass  # implement your persistence logic here


subscriber = sub.AlgorandSubscriber(
    config=sub.AlgorandSubscriberConfig(
        filters=[
            sub.SubscriberConfigFilter(
                name="filter1",
                type="acfg",
                sender="ER7AMZRPD5KDVFWTUUVOADSOWM4RQKEEV2EDYRVSA757UHXOIEKGMBQIVU",
                asset_create=True,
            ),
        ],
        wait_for_block_when_at_tip=True,
        watermark_persistence=sub.in_memory_watermark(),
        sync_behaviour="catchup-with-indexer",
        max_rounds_to_sync=1000,
    ),
    algod_client=algorand.client.algod,
    indexer_client=algorand.client.indexer,
)


def process_transactions(transaction: sub.SubscribedTransaction, _: str) -> None:
    save_transactions([transaction])


subscriber.on("filter1", process_transactions)
subscriber.start()
```