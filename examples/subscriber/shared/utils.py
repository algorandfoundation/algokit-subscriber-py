from __future__ import annotations

from typing import TYPE_CHECKING, Any

from algokit_subscriber import (
    AlgorandSubscriber,
    AlgorandSubscriberConfig,
    SubscriberConfigFilter,
    TransactionFilter,
    WatermarkPersistence,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from algosdk.v2client.algod import AlgodClient

    from algokit_subscriber import SubscribedTransaction


def print_header(title: str) -> None:
    """Print a section header with a decorative border."""
    line = "=" * 60
    print(f"\n{line}")
    print(f"  {title}")
    print(f"{line}\n")


def print_step(step: int, description: str) -> None:
    """Print a numbered step description."""
    print(f"\nStep {step}: {description}")


def print_info(message: str) -> None:
    """Print an informational message."""
    print(f"  [info] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"  [ok] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"  [FAIL] {message}")


def format_algo(micro_algos: float, decimals: int = 6) -> str:
    """Format a microAlgo amount as ALGO."""
    value = float(micro_algos) / 1e6
    return f"{value:.{decimals}f} ALGO"


def shorten_address(address: str, prefix_length: int = 6, suffix_length: int = 4) -> str:
    """Shorten an Algorand address for display."""
    if len(address) <= prefix_length + suffix_length:
        return address
    return f"{address[:prefix_length]}...{address[-suffix_length:]}"


def format_micro_algo(micro_algos: float) -> str:
    """Format a microAlgo amount with locale separator."""
    return f"{int(micro_algos):,} microALGO"


def create_filter_tester(
    algod: AlgodClient,
    watermark_before: int,
) -> Callable[..., list[SubscribedTransaction]]:
    """Create a filter-testing function bound to an algod client and watermark."""

    def test_filter(
        name: str,
        txn_filter: dict[str, Any] | TransactionFilter,
        expected: int | None = None,
        success_msg: str | None = None,
        format_txn: Callable[[SubscribedTransaction], None] | None = None,
    ) -> list[SubscribedTransaction]:
        watermark = watermark_before

        def get_watermark() -> int:
            return watermark

        def set_watermark(w: int) -> None:
            nonlocal watermark
            watermark = w

        if isinstance(txn_filter, dict):
            resolved_filter = TransactionFilter(**txn_filter)
        else:
            resolved_filter = txn_filter

        subscriber = AlgorandSubscriber(
            config=AlgorandSubscriberConfig(
                filters=[
                    SubscriberConfigFilter(
                        name=name,
                        filter=resolved_filter,
                    )
                ],
                sync_behaviour="sync-oldest",
                max_rounds_to_sync=100,
                watermark_persistence=WatermarkPersistence(
                    get=get_watermark,
                    set=set_watermark,
                ),
            ),
            algod_client=algod,
        )

        result = subscriber.poll_once()
        txns = result.subscribed_transactions

        print_info(f"Matched count: {len(txns)}")
        if format_txn:
            for txn in txns:
                format_txn(txn)
        if expected is not None and len(txns) != expected:
            raise RuntimeError(f"{name} filter: expected {expected} matches, got {len(txns)}")
        if success_msg:
            print_success(success_msg)

        return txns

    return test_filter
