from algokit_utils import AlgorandClient
from syrupy.assertion import SnapshotAssertion

from algokit_subscriber.types import subscription as sub

from .transactions import get_subscribed_transactions_for_test

STPF_ROUND = 35600004
STPF_TXN_ID = "G2U5DWQRQV7EGQDAHH62EDY22VYPP4VWM3V2S5BLDNXNWFNKRXMQ"


def test_stpf_from_indexer(mainnet: AlgorandClient, module_snapshot: SnapshotAssertion) -> None:
    txns = get_subscribed_transactions_for_test(
        sub.TransactionSubscriptionParams(
            filters=[sub.TransactionFilter(name="default", type="stpf")],
            max_rounds_to_sync=1,
            current_round=STPF_ROUND + 1,
            sync_behaviour="catchup-with-indexer",
            watermark=STPF_ROUND - 1,
        ),
        algorand=mainnet,
    )

    assert len(txns.subscribed_transactions) == 1
    txn = txns.subscribed_transactions[0]
    assert txn.id_ == STPF_TXN_ID

    assert txn == module_snapshot


def test_stpf_from_algod(mainnet: AlgorandClient, module_snapshot: SnapshotAssertion) -> None:
    txns = get_subscribed_transactions_for_test(
        sub.TransactionSubscriptionParams(
            filters=[sub.TransactionFilter(name="default", type="stpf")],
            max_rounds_to_sync=1,
            current_round=STPF_ROUND + 1,
            sync_behaviour="sync-oldest",
            watermark=STPF_ROUND - 1,
        ),
        algorand=mainnet,
    )

    assert len(txns.subscribed_transactions) == 1
    txn = txns.subscribed_transactions[0]
    assert txn.id_ == STPF_TXN_ID

    assert txn == module_snapshot
