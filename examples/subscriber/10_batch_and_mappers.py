"""Example 10: Batch Handling & Data Mappers

Demonstrates mapper transforms with on_batch and on handler patterns:
- Define a mapper to transform list[SubscribedTransaction] to custom types
- Compare on_batch (fires once per poll) vs on (fires per transaction)
- Verify type safety with mapped data

Prerequisites:
- LocalNet running (via `algokit localnet start`)
"""

from __future__ import annotations

from dataclasses import dataclass

from algokit_utils import AlgoAmount, AlgorandClient, PaymentParams
from shared import (
    ALGOD_CONFIG,
    KMD_CONFIG,
    format_algo,
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
    WatermarkPersistence,
)


@dataclass
class PaymentSummary:
    """Mapped output from SubscribedTransaction for payment txns."""

    id: str
    sender: str
    receiver: str
    amount_in_algos: float
    note: str


def payment_mapper(txns: list[SubscribedTransaction]) -> list[PaymentSummary]:
    """Map raw SubscribedTransactions to PaymentSummary instances."""
    return [
        PaymentSummary(
            id=txn.id_,
            sender=txn.sender,
            receiver=txn.payment_transaction.receiver if txn.payment_transaction else "",
            amount_in_algos=(txn.payment_transaction.amount if txn.payment_transaction else 0)
            / 1_000_000,
            note=txn.note.decode("utf-8") if txn.note else "",
        )
        for txn in txns
    ]


def show_mapped_data(
    batch_items: list[PaymentSummary],
    individual_items: list[PaymentSummary],
) -> None:
    """Step 9: Display batch and individual mapped data."""
    print()
    print("  Batch items (from on_batch):")
    for item in batch_items:
        print_info(
            f"  {item.note}: {item.amount_in_algos} ALGO"
            f" | {shorten_address(item.sender)}"
            f" -> {shorten_address(item.receiver)}"
        )

    print()
    print("  Individual items (from on):")
    for item in individual_items:
        print_info(f"  {item.note}: {item.amount_in_algos} ALGO | id: {item.id[:12]}...")


def print_summary_table(batch_size: int, on_count: int) -> None:
    """Step 10: Print comparison table for on_batch vs on."""
    print()
    w = 57
    h = "\u2500" * w
    print(f"  \u250c{h}\u2510")
    print(f"  \u2502  on_batch(filter_name, handler){' ' * 26}\u2502")
    print(f"  \u2502    - Fires: once per poll{' ' * 31}\u2502")
    print(
        f"  \u2502    - Receives: list[T]"
        f" (array of {batch_size} PaymentSummary items)"
        f"{' ' * 4}\u2502"
    )
    print(f"  \u2502    - Use for: bulk inserts, batch processing{' ' * 11}\u2502")
    print(f"  \u251c{h}\u2524")
    print(f"  \u2502  on(filter_name, handler){' ' * 31}\u2502")
    print(f"  \u2502    - Fires: once per transaction ({on_count} times){' ' * 13}\u2502")
    print(f"  \u2502    - Receives: T (single PaymentSummary item){' ' * 10}\u2502")
    print(f"  \u2502    - Use for: per-item processing, logging{' ' * 13}\u2502")
    print(f"  \u251c{h}\u2524")
    print(f"  \u2502  mapper on filter config{' ' * 31}\u2502")
    print(f"  \u2502    - Transforms: SubscribedTransaction[] -> T[]{' ' * 8}\u2502")
    print(f"  \u2502    - Applied BEFORE both on and on_batch handlers{' ' * 5}\u2502")
    print(f"  \u2502    - Type safety via mapper return type{' ' * 16}\u2502")
    print(f"  \u2514{h}\u2518")
    print()


def setup_and_send(
    algorand: AlgorandClient,
) -> tuple[str, str, int]:
    """Steps 2-3: Create accounts, send 5 payments. Return (sender, receiver, first_round)."""
    # Step 2: Create and fund accounts
    print_step(2, "Create and fund accounts")
    dispenser = algorand.account.localnet_dispenser().addr
    sender = algorand.account.random().addr
    receiver = algorand.account.random().addr
    algorand.send.payment(
        PaymentParams(sender=dispenser, receiver=sender, amount=AlgoAmount(algo=100))
    )
    algorand.send.payment(
        PaymentParams(sender=dispenser, receiver=receiver, amount=AlgoAmount(algo=10))
    )
    print_info(f"Sender: {shorten_address(sender)}")
    print_info(f"Receiver: {shorten_address(receiver)}")
    print_success("Accounts created and funded")

    # Step 3: Send 5 payment transactions with varying amounts and notes
    print_step(3, "Send 5 payment transactions")
    payments = [
        (AlgoAmount(algo=1), "payment-1"),
        (AlgoAmount(algo=2), "payment-2"),
        (AlgoAmount(algo=3), "payment-3"),
        (AlgoAmount(algo=5), "payment-4"),
        (AlgoAmount(algo=8), "payment-5"),
    ]
    first_round: int | None = None
    for amount, note in payments:
        result = algorand.send.payment(
            PaymentParams(
                sender=sender,
                receiver=receiver,
                amount=amount,
                note=note.encode("utf-8"),
            )
        )
        rnd = result.confirmation.confirmed_round
        if first_round is None:
            first_round = rnd
        print_info(f"Sent {note}: {format_algo(amount.micro_algo)} in round {rnd}")
    print_success(f"Sent {len(payments)} payments")
    assert first_round is not None
    return sender, receiver, first_round


def create_and_poll(
    algorand: AlgorandClient,
    sender: str,
    receiver: str,
    first_round: int,
) -> tuple[list[list[PaymentSummary]], list[PaymentSummary]]:
    """Steps 4-6: Configure mapper, create subscriber, poll once."""
    # Step 4: Configure mapper
    print_step(4, "Configure subscriber with mapper")
    watermark = first_round - 1
    print_info(
        "Mapper: SubscribedTransaction[] -> PaymentSummary[]"
        " { id, sender, receiver, amount_in_algos, note }"
    )
    print_success("Mapper defined")

    # Step 5: Create subscriber with on_batch and on handlers
    print_step(5, "Create subscriber with on_batch and on handlers")
    batch_results: list[list[PaymentSummary]] = []
    individual_results: list[PaymentSummary] = []

    def get_wm() -> int:
        return watermark

    def set_wm(w: int) -> None:
        nonlocal watermark
        watermark = w

    subscriber = AlgorandSubscriber(
        config=AlgorandSubscriberConfig(
            filters=[
                SubscriberConfigFilter(
                    name="payments",
                    filter=TransactionFilter(sender=sender, receiver=receiver),
                    mapper=payment_mapper,
                ),
            ],
            sync_behaviour="sync-oldest",
            max_rounds_to_sync=100,
            watermark_persistence=WatermarkPersistence(get=get_wm, set=set_wm),
        ),
        algod_client=algorand.client.algod,
    )

    def handle_batch(batch: list[PaymentSummary], _name: str) -> None:
        batch_results.append(batch)
        print(f"\n  [on_batch] Received batch of {len(batch)} items")

    def handle_item(item: PaymentSummary, _name: str) -> None:
        individual_results.append(item)
        print(f"  [on]      Received item: {item.note} \u2014 {item.amount_in_algos} ALGO")

    subscriber.on_batch("payments", handle_batch)
    subscriber.on("payments", handle_item)
    print_info("on_batch: registered \u2014 fires once per poll with full array")
    print_info("on: registered \u2014 fires once per transaction with individual item")

    # Step 6: Poll once to trigger handlers
    print_step(6, "Poll once \u2014 observe on_batch vs on firing")
    poll_result = subscriber.poll_once()
    print_info(f"Raw matched count: {len(poll_result.subscribed_transactions)}")
    return batch_results, individual_results


def main() -> None:
    print_header("10 \u2014 Batch Handling & Data Mappers")

    # Step 1: Connect to LocalNet
    print_step(1, "Connect to LocalNet")
    algorand = AlgorandClient.from_config(algod_config=ALGOD_CONFIG, kmd_config=KMD_CONFIG)
    status = algorand.client.algod.status()
    print_info(f"Current round: {status.last_round}")
    print_success("Connected to LocalNet")

    sender, receiver, first_round = setup_and_send(algorand)
    batch_results, individual_results = create_and_poll(algorand, sender, receiver, first_round)

    # Step 7: Verify on_batch behavior
    print_step(7, "Verify on_batch behavior")
    print_info(f"on_batch fired: {len(batch_results)} time(s)")
    print_info(f"Batch size: {len(batch_results[0]) if batch_results else 0}")
    assert len(batch_results) == 1, (
        f"Expected on_batch to fire exactly 1 time, got {len(batch_results)}"
    )
    assert len(batch_results[0]) == 5, f"Expected batch size of 5, got {len(batch_results[0])}"
    print_success("on_batch fired once with all 5 items")

    # Step 8: Verify on behavior
    print_step(8, "Verify on behavior")
    print_info(f"on fired: {len(individual_results)} time(s)")
    assert len(individual_results) == 5, (
        f"Expected on to fire 5 times, got {len(individual_results)}"
    )
    print_success("on fired once per transaction (5 times)")

    # Step 9: Demonstrate type safety and mapped data
    print_step(9, "Demonstrate type safety and mapped data")
    show_mapped_data(batch_results[0], individual_results)

    # Step 10: Summary
    print_step(10, "Summary: on_batch vs on")
    print_summary_table(len(batch_results[0]), len(individual_results))

    print_header("Example complete")


if __name__ == "__main__":
    main()
