---
title: ARC-28 Events
description: Subscribe to and receive ARC-28 smart contract events, similar to Ethereum event subscriptions.
---

You can [subscribe to ARC-28 events](../filtering/) for a smart contract, similar to how you can [subscribe to events in Ethereum](https://docs.web3js.org/guides/events_subscriptions/).

Furthermore, you can receive any ARC-28 events that a smart contract call you subscribe to emitted in the [subscribed transaction object](../../guide/subscriptions/#subscribedtransaction).

Both subscription and receiving ARC-28 events work through the use of the `arc28_events` parameter in [`AlgorandSubscriber`](../../guide/subscriber/) and [`get_subscribed_transactions`](../../guide/subscriptions/):

```python
import algokit_subscriber as sub

group1_events = sub.Arc28EventGroup(
    events=[
        sub.Arc28Event(
            name="MyEvent",
            args=[
                sub.Arc28EventArg(type="uint64"),
                sub.Arc28EventArg(type="string"),
            ],
        )
    ]
)

subscriber = sub.AlgorandSubscriber(
    config=sub.AlgorandSubscriberConfig(
        arc28_events={"group1": group1_events},
        # ...
    ),
    # ...
)

# or:

result = sub.get_subscribed_transactions(
    subscription=sub.TransactionSubscriptionParams(
        arc28_events={"group1": group1_events},
        # ...
    ),
    # ...
)
```

See the full API reference for these types:

- [`Arc28EventGroup`](../../api/algokit_subscriber/) - Specifies a group of ARC-28 event definitions along with instructions for when to attempt to process the events
- [`Arc28Event`](../../api/algokit_subscriber/) - The definition of metadata for an ARC-28 event as per the ARC-28 specification
- [`Arc28EventArg`](../../api/algokit_subscriber/) - The definition of an ARC-28 event argument

Each group allows you to apply logic to the applicability and processing of a set of events. This structure allows you to safely process the events from multiple contracts in the same subscriber, or perform more advanced filtering logic to event processing.

When specifying an [ARC-28 event filter](../filtering/), you specify both the `group_name` and `event_name`(s) to narrow down what event(s) you want to subscribe to.

If you want to emit an ARC-28 event from your smart contract see [Emitting ARC-28 Events](../emit-arc28-events/).