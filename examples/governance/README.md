# Subscriber Example: Governance

This example demonstrates how to use the `AlgorandSubscriber` to parse governance commitment transactions. Every 10 seconds, the subscriber will print out all of the governance commitments made since the last sync. The subscriber in this example uses `"sync_behaviour": "catchup-with-indexer"` to catch up because we are expecting to have a large amount of transactions with a common note prefix. This is an example of where the indexer's server-side filtering is useful. It should be noted that the exact same behavior can be achieved without indexer using algod, but indexer allows for a quicker catchup with fewer API calls. This example also only polls the chain every 10 seconds, since it is primarily useful for historical data and we don't care about live data.

## Governance Prefix

This example uses the `af/gov1` governance prefix to find governance transactions. For more information on Algorand Governance transactions, see the [Govenor's Guide](https://forum.algorand.org/t/governors-guide-2021-2024/12013).

## Running the example

To run the example, execute the following commands:

### Install dependencies

```bash
poetry install
```

### Run the script

```bash
poetry run python governance.py
```
