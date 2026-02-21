---
title: Watermarking and Resilience
description: Use round watermarks to create resilient syncing services that recover from outages.
---

# Watermarking and Resilience

You can create reliable syncing / indexing services through a simple round watermarking capability that allows you to create resilient syncing services that can recover from an outage.

This works through the use of the `watermark_persistence` parameter in [`AlgorandSubscriber`](../../guide/subscriber/) and `watermark` parameter in [`get_subscribed_transactions`](../../guide/subscriptions/):

```python
import algokit_subscriber as sub


def get_saved_watermark() -> int:
    # Return the watermark from a persistence store e.g. database, redis, file system, etc.
    pass


def save_watermark(new_watermark: int) -> None:
    # Save the watermark to a persistence store e.g. database, redis, file system, etc.
    pass


subscriber = sub.AlgorandSubscriber(
    config=sub.AlgorandSubscriberConfig(
        watermark_persistence=sub.WatermarkPersistence(
            get=get_saved_watermark,
            set=save_watermark,
        ),
        # ... other configuration options
    ),
    # ...
)

# or when using get_subscribed_transactions directly:

watermark = get_saved_watermark()
result = sub.get_subscribed_transactions(
    subscription=sub.TransactionSubscriptionParams(watermark=watermark, ...),
    ...
)
save_watermark(result.new_watermark)
```

By using a persistence store, you can gracefully respond to an outage of your subscriber. The next time it starts it will pick back up from the point where it last persisted. It's worth noting this provides **at-least-once** delivery semantics so you need to handle duplicate events.

Alternatively, if you want to create at-most-once delivery semantics you could use the [transactional outbox pattern](https://microservices.io/patterns/data/transactional-outbox.html) and wrap a unit of work from an ACID persistence store (e.g. a SQL database with a serializable or repeatable read transaction) around the watermark retrieval, transaction processing and watermark persistence so the processing of transactions and watermarking of a single poll happens in a single atomic transaction.

## In-Memory Watermarking

If you are doing a quick test or creating an ephemeral subscriber that just needs to exist in-memory and doesn't need to recover resiliently (useful with `sync_behaviour` of `skip-sync-newest` for instance) then you can use the `in_memory_watermark()` helper:

```python
import algokit_subscriber as sub

subscriber = sub.AlgorandSubscriber(
    config=sub.AlgorandSubscriberConfig(
        watermark_persistence=sub.in_memory_watermark(),  # optionally pass initial watermark
        # ... other configuration options
    ),
    # ...
)

# or when using get_subscribed_transactions directly:

watermark = 0
result = sub.get_subscribed_transactions(
    subscription=sub.TransactionSubscriptionParams(watermark=watermark, ...),
    ...
)
watermark = result.new_watermark
```