"""Example 01: Basic Poll Once

Demonstrates a single poll_once() call with a sender filter.
Creates a funded sender account, sends 2 self-payment transactions,
then uses AlgorandSubscriber to find and verify the matched transactions.

Prerequisites:
- LocalNet running (via `algokit localnet start`)
"""

from algokit_utils import AlgoAmount, AlgorandClient, PaymentParams
from shared import (
    ALGOD_CONFIG,
    KMD_CONFIG,
    print_header,
    print_info,
    print_step,
    print_success,
    shorten_address,
)

from algokit_subscriber import (
    AlgorandSubscriber,
    AlgorandSubscriberConfig,
    SubscriberConfigFilter,
    TransactionFilter,
    in_memory_watermark,
)


def main() -> None:
    print_header("01 — Basic Poll Once")

    # Step 1: Connect to LocalNet
    print_step(1, "Connect to LocalNet")
    algorand = AlgorandClient.from_config(algod_config=ALGOD_CONFIG, kmd_config=KMD_CONFIG)
    status = algorand.client.algod.status()
    print_info(f"Current round: {status.last_round}")
    print_success("Connected to LocalNet")

    # Step 2: Create and fund sender account
    print_step(2, "Create and fund sender account")
    sender = algorand.account.random().addr
    dispenser = algorand.account.localnet_dispenser().addr
    algorand.send.payment(
        PaymentParams(
            sender=dispenser,
            receiver=sender,
            amount=AlgoAmount(algo=10),
        )
    )
    print_info(f"Sender: {shorten_address(sender)}")

    # Step 3: Send 2 payment transactions
    print_step(3, "Send 2 payment transactions")
    txn1 = algorand.send.payment(
        PaymentParams(
            sender=sender,
            receiver=sender,
            amount=AlgoAmount(algo=1),
            note=b"poll-once txn 1",
        )
    )
    print_info(f"Txn 1 ID: {txn1.tx_id}")
    print_info(f"Txn 1 round: {txn1.confirmation.confirmed_round}")

    txn2 = algorand.send.payment(
        PaymentParams(
            sender=sender,
            receiver=sender,
            amount=AlgoAmount(algo=1),
            note=b"poll-once txn 2",
        )
    )
    print_info(f"Txn 2 ID: {txn2.tx_id}")
    print_info(f"Txn 2 round: {txn2.confirmation.confirmed_round}")
    print_success("Sent 2 payment transactions")

    # Step 4: Create subscriber with in-memory watermark
    print_step(4, "Create AlgorandSubscriber")
    watermark_before = txn1.confirmation.confirmed_round - 1

    subscriber = AlgorandSubscriber(
        config=AlgorandSubscriberConfig(
            filters=[
                SubscriberConfigFilter(
                    name="payments",
                    filter=TransactionFilter(sender=sender),
                )
            ],
            sync_behaviour="sync-oldest",
            max_rounds_to_sync=100,
            watermark_persistence=in_memory_watermark(watermark_before),
        ),
        algod_client=algorand.client.algod,
    )
    print_info("Sync behaviour: sync-oldest")
    print_info(f"Initial watermark: {watermark_before}")
    print_success("Subscriber created")

    # Step 5: Poll once and inspect result
    print_step(5, "Poll once and inspect result")
    result = subscriber.poll_once()

    print_info(
        f"syncedRoundRange: [{result.synced_round_range[0]}, {result.synced_round_range[1]}]"
    )
    print_info(f"currentRound: {result.current_round}")
    print_info(f"startingWatermark: {result.starting_watermark}")
    print_info(f"newWatermark: {result.new_watermark}")
    print_info(f"subscribedTransactions count: {len(result.subscribed_transactions)}")

    # Step 6: Block metadata
    print_step(6, "Block metadata")
    if result.block_metadata and len(result.block_metadata) > 0:
        for block in result.block_metadata:
            print_info(f"Block round: {block.round}")
    else:
        print_info("Block metadata: none returned")

    # Step 7: Verify exactly 2 transactions matched
    print_step(7, "Verify matched transactions")
    assert len(result.subscribed_transactions) == 2, (
        f"Expected 2 transactions, got {len(result.subscribed_transactions)}"
    )
    print_success("Exactly 2 transactions matched")

    # Step 8: Print matched transaction IDs
    print_step(8, "Matched transaction IDs")
    for txn in result.subscribed_transactions:
        print_info(f"Matched txn: {txn.id_}")

    print_header("Example complete")


if __name__ == "__main__":
    main()
