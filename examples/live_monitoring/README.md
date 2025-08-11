# Subscriber Example: Live Monitoring

This example demonstrates how to use the `AlgorandSubscriber` to get live transactions from the Algorand blockchain.

Each round, the subscriber will print out all of the USDC and ALGO transactions that have ocurred.

This is an example of using the subscriber for live monitoring where you don't care about historical data. This behavior is primarily driven by the `"sync_behaviour": "skip-sync-newest"` configuration which skips syncing older blocks. Since we don't care about historical data, the watermark of the last round processed is not persisted and only a non-archival algod is required for the subscriber to function. This makes this setup lightweight with low infrastructure requirements.

## Running the example

To run the example, execute the following commands:

### Install dependencies

```bash
poetry install
```

### Run the script

```bash
poetry run python live_monitoring.py
```
