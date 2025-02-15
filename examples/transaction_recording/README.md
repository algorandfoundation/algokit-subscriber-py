# Subscriber Example: Transaction Record

This example demonstrates how to use the `AlgorandSubscriber` to record all of the balance changes for a given account. This example uses the filesystem to persist the watermark and record transactions in a CSV file. This example makes use of the `"balance_changes"` filter option which will include ANY transaction that affects the balance of the given account. This example uses `"sync_behaviour": "sync-oldest"` to ensure that we get all historical data from an archival node. An indexer could be used for catchup, but due to the complex nature of the query it would not save any API calls like it would with a more simple query (such as the one in the [governance example](../governance/README.md)).

## Created Files

`watermark` will be created with the last processed round and updated with each new round processed.

`transactions.csv` will be created with the header `round,sender,receiver,amount` and will append a new row for each transaction processed.

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
