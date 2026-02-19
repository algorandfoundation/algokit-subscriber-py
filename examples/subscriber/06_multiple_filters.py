"""Example 06: Multiple Named Filters

Demonstrates multiple named filters with deduplication:
- Define multiple filters on a single subscriber
- Verify transactions are deduplicated across filters
- Inspect filtersMatched on each transaction

Prerequisites:
- LocalNet running (via `algokit localnet start`)
"""

from algokit_utils import AlgoAmount, AlgorandClient, PaymentParams
from shared import (
    ALGOD_CONFIG,
    KMD_CONFIG,
    format_micro_algo,
    print_header,
    print_info,
    print_step,
    print_success,
    shorten_address,
)

from algokit_subscriber import (
    AlgorandSubscriber,
    AlgorandSubscriberConfig,
    SubscribedTransaction,
    SubscriberConfigFilter,
    TransactionFilter,
    in_memory_watermark,
)


def find_txn_by_note(txns: list[SubscribedTransaction], note: str) -> SubscribedTransaction | None:
    """Find a transaction by its note content."""
    note_bytes = note.encode()
    for t in txns:
        if t.note == note_bytes:
            return t
    return None


def verify_filters_matched(
    txn: SubscribedTransaction,
    note: str,
    expected_filters: list[str],
) -> None:
    """Assert filters_matched contains exactly the expected filter names."""
    actual = sorted(txn.filters_matched)
    expected = sorted(expected_filters)
    assert actual == expected, f"{note} expected filters {expected}, got {actual}"
    print_success(f"{note} matched: {', '.join(expected_filters)}")


def main() -> None:
    print_header("06 — Multiple Named Filters")

    # Step 1: Connect to LocalNet
    print_step(1, "Connect to LocalNet")
    algorand = AlgorandClient.from_config(algod_config=ALGOD_CONFIG, kmd_config=KMD_CONFIG)
    status = algorand.client.algod.status()
    print_info(f"Current round: {status.last_round}")
    print_success("Connected to LocalNet")

    # Step 2: Create and fund accounts
    print_step(2, "Create and fund accounts (sender, receiver)")
    dispenser = algorand.account.localnet_dispenser().addr
    sender = algorand.account.random().addr
    receiver = algorand.account.random().addr
    for acct in (sender, receiver):
        algorand.send.payment(
            PaymentParams(
                sender=dispenser,
                receiver=acct,
                amount=AlgoAmount(algo=100),
            )
        )
    print_info(f"Sender:   {shorten_address(sender)}")
    print_info(f"Receiver: {shorten_address(receiver)}")
    print_success("Accounts created and funded")

    # Step 3: Send 5 transactions with varying filter overlap
    print_step(3, "Send 5 transactions with varying filter overlap")
    txn_specs: list[tuple[str, str, int, bytes, str]] = [
        (sender, receiver, 5_000_000, b"multi-01", "sender->receiver 5A (all 3)"),
        (sender, sender, 1_000_000, b"multi-02", "sender->sender 1A (from-sender)"),
        (receiver, sender, 4_000_000, b"multi-03", "receiver->sender 4A (large-txns)"),
        (
            sender,
            receiver,
            1_000_000,
            b"multi-04",
            "sender->receiver 1A (from-sender + to-receiver)",
        ),
        (receiver, sender, 500_000, b"multi-05", "receiver->sender 0.5A (none)"),
    ]

    first_confirmed_round: int | None = None
    for i, (s, r, amount, note, desc) in enumerate(txn_specs):
        result = algorand.send.payment(
            PaymentParams(
                sender=s,
                receiver=r,
                amount=AlgoAmount(micro_algo=amount),
                note=note,
            )
        )
        if first_confirmed_round is None:
            first_confirmed_round = result.confirmation.confirmed_round
        print_info(f"Txn {i + 1}: {desc}")
    assert first_confirmed_round is not None
    print_success(f"Sent {len(txn_specs)} transactions")

    # Step 4: Create subscriber with 3 named filters
    print_step(4, "Create subscriber with 3 named filters")
    watermark_before = first_confirmed_round - 1
    subscriber = AlgorandSubscriber(
        config=AlgorandSubscriberConfig(
            filters=[
                SubscriberConfigFilter(
                    name="from-sender",
                    filter=TransactionFilter(sender=sender),
                ),
                SubscriberConfigFilter(
                    name="to-receiver",
                    filter=TransactionFilter(receiver=receiver),
                ),
                SubscriberConfigFilter(
                    name="large-txns",
                    filter=TransactionFilter(min_amount=3_000_000),
                ),
            ],
            watermark_persistence=in_memory_watermark(watermark_before),
            sync_behaviour="sync-oldest",
            max_rounds_to_sync=100,
        ),
        algod_client=algorand.client.algod,
    )
    print_info("Filter 1: 'from-sender' — sender = sender account")
    print_info("Filter 2: 'to-receiver' — receiver = receiver account")
    print_info("Filter 3: 'large-txns'  — minAmount = 3,000,000 microAlgo")
    print_success("Subscriber created with 3 named filters")

    # Step 5: Poll once and inspect results
    print_step(5, "Poll once and inspect deduplicated results")
    poll_result = subscriber.poll_once()
    txns = poll_result.subscribed_transactions
    print_info(f"Total subscribed transactions: {len(txns)}")

    # Step 6: Inspect filtersMatched per transaction
    print_step(6, "Inspect filtersMatched per transaction")
    for txn in txns:
        note_str = txn.note.decode() if txn.note else ""
        amt = txn.payment_transaction.amount if txn.payment_transaction else 0
        filters = ", ".join(txn.filters_matched)
        print_info(f"{note_str}: {format_micro_algo(amt)} | filtersMatched: [{filters}]")

    # Step 7: Verify deduplication
    print_step(7, "Verify deduplication")
    txn1_matches = [t for t in txns if t.note == b"multi-01"]
    assert len(txn1_matches) == 1, f"Dedup failed: multi-01 appears {len(txn1_matches)} times"
    matched_count = len(txn1_matches[0].filters_matched)
    print_info(
        f'Txn "multi-01": appears {len(txn1_matches)} time (matched {matched_count} filters)'
    )
    print_success("Transaction appears once even though it matched all 3 filters")

    # Step 8: Verify filtersMatched accuracy
    verify_filters_on_txns(txns)

    # Step 9: Summary table
    print_summary_table(txns)

    print_header("Example complete")


def print_summary_table(txns: list[SubscribedTransaction]) -> None:
    """Print a summary table of matched transactions."""
    print_step(9, "Summary table")
    print()
    print("  ┌────────────┬─────────────────────────┬───────────────────────────────────────┐")
    print("  │ Note       │ Amount                  │ Filters Matched                       │")
    mid = "  ├────────────┼─────────────────────────┼───────────────────────────────────────┤"
    print(mid)
    for txn in txns:
        note = txn.note.decode() if txn.note else ""
        amt = txn.payment_transaction.amount if txn.payment_transaction else 0
        filters = ", ".join(txn.filters_matched)
        print(f"  │ {note:<10} │ {format_micro_algo(amt):<23} │ {filters:<37} │")
    print(mid)
    excluded = "(no match — excluded)"
    print(f"  │ {'multi-05':<10} │ {'500000 microALGO':<23} │ {excluded:<37} │")
    print("  └────────────┴─────────────────────────┴───────────────────────────────────────┘")
    print()


def verify_filters_on_txns(txns: list[SubscribedTransaction]) -> None:
    """Verify filtersMatched accuracy for each transaction."""
    print_step(8, "Verify filtersMatched accuracy")

    txn1 = find_txn_by_note(txns, "multi-01")
    assert txn1 is not None
    verify_filters_matched(txn1, "multi-01", ["from-sender", "to-receiver", "large-txns"])

    txn2 = find_txn_by_note(txns, "multi-02")
    assert txn2 is not None
    verify_filters_matched(txn2, "multi-02", ["from-sender"])

    txn3 = find_txn_by_note(txns, "multi-03")
    assert txn3 is not None
    verify_filters_matched(txn3, "multi-03", ["large-txns"])

    txn4 = find_txn_by_note(txns, "multi-04")
    assert txn4 is not None
    verify_filters_matched(txn4, "multi-04", ["from-sender", "to-receiver"])

    txn5 = find_txn_by_note(txns, "multi-05")
    assert txn5 is None, "multi-05 should not match any filter"
    print_success("multi-05 correctly excluded (matched no filters)")

    assert len(txns) == 4, f"Expected 4 deduplicated transactions, got {len(txns)}"
    print_success("Exactly 4 deduplicated transactions returned")


if __name__ == "__main__":
    main()
