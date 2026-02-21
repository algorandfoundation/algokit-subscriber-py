---
title: Quick Start
description: Get up and running with algokit-subscriber in minutes.
---

# Quick Start

## Installation

```bash
pip install algokit-subscriber
```

Or with `uv`:

```bash
uv add algokit-subscriber
```

## Basic Example

```python
import algokit_subscriber as sub
from algokit_utils import AlgorandClient

testnet = AlgorandClient.testnet()

subscriber = sub.AlgorandSubscriber(
    config=sub.AlgorandSubscriberConfig(
        filters=[
            sub.SubscriberConfigFilter(
                name="filter1",
                filter=sub.TransactionFilter(
                    type="pay",
                    sender="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ",
                ),
            ),
        ],
        watermark_persistence=sub.in_memory_watermark(),
        sync_behaviour="skip-sync-newest",
        max_rounds_to_sync=100,
    ),
    algod_client=testnet.client.algod,
)

# Set up event listener
subscriber.on("filter1", lambda transaction, _: print(f"Received: {transaction.id_}"))

# Handle errors
subscriber.on_error(lambda error, _: print(f"Error: {error}"))

# Either: poll once (for cron / Lambda)
result = subscriber.poll_once()
print(f"Polled {len(result.subscribed_transactions)} transactions")

# Or: start continuous polling (for long-running processes)
# subscriber.start()
```

## Entry Points

There are two entry points into the subscriber functionality:

- **[`AlgorandSubscriber`](../guide/subscriber/)** — Higher-level class that handles continuous polling, event listeners, error handling, and watermarking orchestration. Start here for most use cases.
- **[`get_subscribed_transactions`](../guide/subscriptions/)** — Lower-level function for a single subscription poll. Use when you control scheduling yourself (e.g. cron, Lambda).

Both are first-class supported. We recommend starting with `AlgorandSubscriber` since it's easier to use and covers the majority of use cases.

## Programming Model

`AlgorandSubscriber` is modelled similarly to an event emitter. You:

1. Create a subscriber with a configuration that defines your filters and sync behaviour
2. Register event listeners with `on()`, `on_batch()`, `on_poll()`, etc.
3. Call `start()` for continuous polling or `poll_once()` for a single poll

The subscriber handles watermarking, error recovery, and polling frequency for you.

## Next Steps

- **[AlgorandSubscriber guide](../guide/subscriber/)** — Full API for the subscriber class
- **[get_subscribed_transactions guide](../guide/subscriptions/)** — Full API for the lower-level function
- **[Sync Behaviour](../concepts/sync-behaviour/)** — How to control what rounds are processed
- **[Filtering](../concepts/filtering/)** — Fine-grained transaction filtering options