from pathlib import Path

from algokit_subscriber.subscriber import AlgorandSubscriber
from algokit_subscriber.types.subscription import SubscribedTransaction
from algokit_utils.beta.algorand_client import AlgorandClient

algorand = AlgorandClient.main_net()

# The desired address to track
track_address = "PDS6KDTDQBBIL34FZSZWL3CEO454VKAMGWRPPP2D52W52WJW2OBDUQJRZM"

# The list of balance changes to write to the CSV file
balance_changes = []

# The directory of this file
this_dir = Path(__file__).parent

watermark_file = this_dir / "watermark"

# If watermark file doesn't exist, create it with a value of 0
if not watermark_file.exists():
    watermark_file.write_text("43932536")

# The CSV file we will write all balance changes of our tracked address to
csv_file = this_dir / "transactions.csv"
if not csv_file.exists():
    csv_file.write_text("round,txn_id,asset_id,amount\n")


def get_watermark() -> int:
    """
    The get_watermark tells the subscriber what the last processed block is
    We are using the filesystem to ensure the value is persisted in the event of failures, power outages, etc.
    """
    return int(watermark_file.read_text())


def set_watermark(new_watermark: int) -> None:
    """
    Write the new transactions to the CSV file and then write the new watermark value to the watermark file
    This order is important to ensure we are not increasing the watermark value if we fail to write the transactions to the CSV file
    """
    csv_lines = "\n".join(",".join(str(v) for v in bc) for bc in balance_changes)
    with Path.open(csv_file, "a") as f:
        f.write(csv_lines)
        if csv_lines:
            f.write("\n")

    watermark_file.write_text(str(new_watermark))
    balance_changes.clear()


subscriber = AlgorandSubscriber(
    algod_client=algorand.client.algod,
    indexer_client=algorand.client.indexer,
    config={
        "filters": [
            {
                "name": "Tracked Address",
                # Only match non-zero ALGO transfers
                "filter": {
                    "balance_changes": [
                        {
                            "address": track_address,
                        },
                    ],
                },
            },
        ],
        # Once we are caught up, always wait until the next block is available and process it immediately once available
        "wait_for_block_when_at_tip": True,
        # The watermark persistence functions are used to get and set the watermark
        "watermark_persistence": {"get": get_watermark, "set": set_watermark},
        # Sync starting from the last watermark using an archival algod node
        "sync_behaviour": "sync-oldest",
    },
)


def record_transaction(transaction: SubscribedTransaction, _: str) -> None:
    """
    This is an EventListener callback. We use the .on function below to attach this callback to specific events.

    Every EventListener callback will receive two arguments:
    * The transaction data
    * The filter name (from the 'filters' list) that the transaction matched (not used in this example)
    """
    global balance_changes  # noqa: PLW0602

    for bc in transaction["balance_changes"]:
        balance_changes.append(
            [
                transaction["confirmed-round"],
                transaction["id"],
                bc["asset_id"],
                bc["amount"],
            ]
        )


# Attach the callback to the events we are interested in
subscriber.on("Tracked Address", record_transaction)

# Start the subscriber
subscriber.start()
