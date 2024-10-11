<div align="center">
<a href="https://github.com/algorandfoundation/algokit-subscriber-py"><img src="https://bafybeidbb3a7cgn3unoz4oouk2jme4eavqgqtnskfr4bqhbjku3s52de4a.ipfs.w3s.link/algokit-subscriber-logo.png" width=60%></a>
</div>

<p align="center">
    <a target="_blank" href="https://algorandfoundation.github.io/algokit-subscriber-py/"><img src="https://img.shields.io/badge/docs-repository-74dfdc?logo=github&style=flat.svg" /></a>
    <a target="_blank" href="https://developer.algorand.org/algokit/"><img src="https://img.shields.io/badge/learn-AlgoKit-74dfdc?logo=algorand&mac=flat.svg" /></a>
    <a target="_blank" href="https://github.com/algorandfoundation/algokit-subscriber-py"><img src="https://img.shields.io/github/stars/algorandfoundation/algokit-subscriber-py?color=74dfdc&logo=star&style=flat" /></a>
    <a target="_blank" href="https://developer.algorand.org/algokit/"><img  src="https://api.visitorbadge.io/api/visitors?path=https%3A%2F%2Fgithub.com%2Falgorandfoundation%2Falgokit-subscriber-py&countColor=%2374dfdc&style=flat" /></a>
</p>

---

This library a simple, but flexible / configurable Algorand transaction subscription / indexing mechanism. It allows you to quickly create Python services that follow or subscribe to the Algorand Blockchain.

> npm install @algorandfoundation/algokit-subscriber

[Documentation](./docs/README.md)

## Quick start

```python
# Create subscriber
subscriber = AlgorandSubscriber(
  {
    "filters": [
      {
        "name": "filter1",
        "filter": {
          "type": "pay",
          "sender": "ABC...",
        },
      },
    ],
    # ... other options (use intellisense to explore)
  },
  algod,
  optional_indexer
);

# Set up subscription(s)
def on_filter1(transaction, event_name):
    ...

subscriber.on("filter1", on_filter1)

# Either: Start the subscriber (if in long-running process)
subscriber.start();

# OR: Poll the subscriber (if in cron job / periodic lambda)
subscriber.pollOnce();
```

## Key features

- **Notification _and_ indexing** - You have fine-grained control over the syncing behaviour and can control the number of rounds to sync at a time, the pattern of syncing i.e. start from the beginning of the chain, or start from the tip; drop stale records if your service can't keep up or keep syncing from where you are up to; etc.
- **Low latency processing** - When your service has caught up to the tip of the chain it can optionally wait for new rounds so you have a low latency reaction to a new round occurring
- **Watermarking and resilience** - You can create reliable syncing / indexing services through a simple round watermarking capability that allows you to create resilient syncing services that can recover from an outage
- **Extensive subscription filtering** - You can filter by transaction type, sender, receiver, note prefix, apps (ID, creation, on complete, ARC-4 method signature, call arguments, ARC-28 events), assets (ID, creation, amount transferred range), transfers (amount transferred range) and balance changes (algo and assets)
- **ARC-28 event subscription support** - You can subscribe to ARC-28 events for a smart contract
- **Balance change support** - Subscribed transactions will have all algo and asset balance changes calculated for you and you can also subscribe to balance changes that meet certain criteria
- **First-class inner transaction support** - Your filter will find arbitrarily nested inner transactions and return that transaction (indexer can't do this!)
- **State-proof support** - You can subscribe to state proof transactions
- **Simple programming model** - It's really easy to use and consume through easy to use, type-safe methods and objects and subscribed transactions have a comprehensive and familiar model type with all relevant/useful information about that transaction (including things like transaction id, round number, created asset/app id, app logs, etc.) modelled on the indexer data model (which is used regardless of whether the transactions come from indexer or algod so it's a consistent experience)
- **Easy to deploy** - You have full control over how you want to deploy and use the subscriber; it will work with whatever persistence (e.g. sql, no-sql, etc.), queuing/messaging (e.g. queues, topics, buses, web hooks, web sockets) and compute (e.g. serverless periodic lambdas, continually running containers, virtual machines, etc.) services you want to use
- **Fast initial index** - There is an indexer catch up mode that allows you to use indexer to catch up to the tip of the chain in seconds or minutes rather than days; alternatively, if you prefer to just use algod and not indexer that option is available too!

## Balance change notes

The balance change semantics work mostly as expected, however the sematics around asset creation and destruction warrants further clarification.

When an asset is created, the full asset supply is attributed to the asset creators account.

The balance change for an asset create transaction will be as below:

```py
{
  "address": "VIDHG4SYANCP2GUQXXSFSNBPJWS4TAQSI3GH4GYO54FSYPDIBYPMSF7HBY", # The asset creator
  "asset_id": 2391, # The created asset id
  "amount": 100000, # Full asset supply of the created asset
  "roles": [BalanceChangeroles.AssetCreator]
}
```

When an asset is destroyed, the full asset supply must be in the asset creators account and the asset manager must send the destroy transaction.
Unfortunately we cannot determine the asset creator or full asset supply from the transaction data. As a result the balance change will always be attributed to the asset manager and will have a 0 amount.
If you need to account for the asset supply being destroyed from the creators account, you'll need to handle this separately.

The balance change for an asset destroy transaction will be as below:

```python
{
  "address": "PIDHG4SYANCP2GUQXXSFSNBPJWS4TAQSI3GH4GYO54FSYPDIBYPMSF7HBY", # The asset destroyer, which will always be the asset manager
  "assetId": 2391, # The destroyed asset id
  "amount": 0, # This value will always be 0
  "roles": [BalanceChangeroles.AssetDestroyer]
}
```

## Examples

### Data History Museum index

The following code, when algod is pointed to TestNet, will find all transactions emitted by the [Data History Museum](https://datahistory.org) since the beginning of time in _seconds_ and then find them in real-time as they emerge on the chain.

The watermark is stored in-memory so this particular example is not resilient to restarts. To change that you can implement proper persistence of the watermark. There is [an example that uses the file system](./examples/data-history-museum/) to demonstrate this.

```python
algorand = AlgorandClient.testnet()

# The watermark is used to track how far the subscriber has processed transactions
watermark = 0

def get_watermark() -> int:
    return watermark

def set_watermark(new_watermark: int) -> None:
    global watermark
    watermark = new_watermark

subscriber = AlgorandSubscriber(
    # algod is used to get the latest transactions once the subscriber has caught up to the network
    algod_client=algorand.client.algod,
    config={
        "filters": [
            {
                "name": "dhm-asset",
                "filter": {
                    # Match asset configuration transactions
                    "type": "acfg",
                    # Data History Museum creator account on TestNet
                    "sender": "ER7AMZRPD5KDVFWTUUVOADSOWM4RQKEEV2EDYRVSA757UHXOIEKGMBQIVU",
                },
            }
        ],
        "frequency_in_seconds": 5,
        "max_rounds_to_sync": 100,
        "sync_behaviour": "catchup-with-indexer",
        "watermark_persistence": {"get": get_watermark, "set": set_watermark},
    },
    # indexer is used to get historical transactions
    indexer_client=algorand.client.indexer,
)

def process_dhm_assets(transactions: list[SubscribedTransaction], filter_name: str) -> None:
    print(f"Received {len(transactions)} asset changes")
    # ... do stuff with the transactions

# Attach our callback to the 'dhm-asset' filter
subscriber.on_batch("dhm-asset", process_dhm_assets)

def handle_error(error: Exception) -> None:
    print(f"An error occurred: {error}")

# Attach the error handler
subscriber.on_error(handle_error)

# Start the subscriber
subscriber.start()
```

### USDC real-time monitoring

The following code, when algod is pointed to MainNet, will find all transfers of [USDC](https://www.circle.com/en/usdc-multichain/algorand) that are greater than $1 and it will poll every 1s for new transfers.

```python
from algokit_subscriber import AlgorandSubscriber
from algokit_subscriber.types import SubscribedTransaction
from algokit_utils import AlgorandClient

algorand = AlgorandClient.main_net()

# The watermark is used to track how far the subscriber has processed transactions
watermark = 0

def get_watermark() -> int:
    return watermark

def set_watermark(new_watermark: int) -> None:
    global watermark
    watermark = new_watermark

subscriber = AlgorandSubscriber(
    algod_client=algorand.client.algod,
    config={
        "filters": [
            {
                "name": "usdc",
                "filter": {
                    "type": "axfer",
                    "asset_id": 31566704,  # MainNet: USDC
                    "min_amount": 1_000_000,  # $1
                },
            }
        ],
        "wait_for_block_when_at_tip": True,
        "sync_behaviour": "skip-sync-newest",
        "watermark_persistence": {"get": get_watermark, "set": set_watermark},
    },
)

def process_usdc_transfer(transfer: SubscribedTransaction, filter_name: str) -> None:
    asset_transfer = transfer.get("asset-transfer-transaction", {})
    amount = asset_transfer.get("amount", 0) / 1_000_000
    print(
        f"{transfer['sender']} sent {asset_transfer.get('receiver')} "
        f"USDC${amount:.2f} in transaction {transfer['id']}"
    )

# Attach our callback to the 'usdc' filter
subscriber.on("usdc", process_usdc_transfer)

def handle_error(error: Exception) -> None:
    print(f"An error occurred: {error}")

# Attach the error handler
subscriber.on_error(handle_error)

# Start the subscriber
subscriber.start()
```
