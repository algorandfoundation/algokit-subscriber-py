---
title: Subscription Filtering
description: Fine-grained transaction filtering by type, sender, receiver, app, asset, ARC-28 events, and more.
---

This library has extensive filtering options available to you so you can have fine-grained control over which transactions you are interested in.

There is a core type [`TransactionFilter`](../../guide/subscriptions/#transactionfilter) used to specify the filters:

```python
import algokit_subscriber as sub

subscriber = sub.AlgorandSubscriber(
    config=sub.AlgorandSubscriberConfig(
        filters=[
            sub.SubscriberConfigFilter(
                name="filterName",
                # Filter properties...
            ),
        ],
        sync_behaviour=...,
        watermark_persistence=...,
    ),
)
# or:
sub.get_subscribed_transactions(
    subscription=sub.TransactionSubscriptionParams(
        filters=[
            sub.TransactionFilter(
                name="filterName",
                # Filter properties...
            ),
        ],
    ),
)
```

Currently this allows you to filter based on any combination (AND logic) of:

- **Transaction type** e.g. `sub.TransactionFilter(name="filter", type="axfer")` or `sub.TransactionFilter(name="filter", type=["axfer", "pay"])`
- **Account** (sender and receiver) e.g. `sub.TransactionFilter(name="filter", sender="ABCDE..F")` or `sub.TransactionFilter(name="filter", sender=["ABCDE..F", "ZYXWV..A"])` and `sub.TransactionFilter(name="filter", receiver="12345..6")`
- **Note prefix** e.g. `sub.TransactionFilter(name="filter", note_prefix="xyz")`
- **Apps**
  - ID e.g. `sub.TransactionFilter(name="filter", app_id=54321)` or `sub.TransactionFilter(name="filter", app_id=[54321, 12345])`
  - Creation e.g. `sub.TransactionFilter(name="filter", app_create=True)`
  - Call on-complete(s) e.g. `sub.TransactionFilter(name="filter", app_on_complete="optin")` or `sub.TransactionFilter(name="filter", app_on_complete=["optin", "noop"])`
  - ARC4 method signature(s) e.g. `sub.TransactionFilter(name="filter", method_signature="MyMethod(uint64,string)")`
  - Call arguments e.g.
    ```python
    sub.TransactionFilter(
        name="filter",
        app_call_arguments_match=lambda app_call_arguments:
            app_call_arguments is not None
            and len(app_call_arguments) > 1
            and app_call_arguments[1].decode("utf-8") == "hello_world"
    )
    ```
  - Emitted ARC-28 event(s) e.g.
    ```python
    sub.TransactionFilter(
        name="filter",
        arc28_events=[sub.Arc28EventFilter(group_name="group1", event_name="MyEvent")]
    )
    ```
    Note: For this to work you need to [specify ARC-28 events in the subscription config](../arc28-events/).

- **Assets**
  - ID e.g. `sub.TransactionFilter(name="filter", asset_id=123456)` or `sub.TransactionFilter(name="filter", asset_id=[123456, 456789])`
  - Creation e.g. `sub.TransactionFilter(name="filter", asset_create=True)`
  - Amount transferred (min and/or max) e.g. `sub.TransactionFilter(name="filter", type="axfer", min_amount=1, max_amount=100)`
  - Balance changes e.g. `sub.TransactionFilter(name="filter", balance_changes=[sub.BalanceChangeFilter(asset_id=[15345, 36234], role=[sub.BalanceChangeRole.Sender], address="ABC...", min_amount=1, max_amount=2)])`
- **Algo transfers** (pay transactions)
  - Amount transferred (min and/or max) e.g. `sub.TransactionFilter(name="filter", type="pay", min_amount=1, max_amount=100)`
  - Balance changes e.g. `sub.TransactionFilter(name="filter", balance_changes=[sub.BalanceChangeFilter(role=[sub.BalanceChangeRole.Sender], address="ABC...", min_amount=1, max_amount=2)])`

## Multiple Filters and OR Logic

You can supply multiple named filters as a list. A filter name can be used multiple times to create an OR filter (transactions matching any filter with the same name will be returned). When subscribed transactions are returned each transaction will have a `filters_matched` property that will have a list of any filter name(s) that caused that transaction to be returned.