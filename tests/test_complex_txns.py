from algokit_utils import AlgorandClient
from syrupy.assertion import SnapshotAssertion

from algokit_subscriber.types import subscription as sub

from .transactions import (
    get_subscribed_transactions_for_test,
)

NESTED_INNER_ROUND = 35214367
NESTED_INNER_APP = 1390675395
NESTED_INNER_ID = "QLYC4KMQW5RZRA7W5GYCJ4CUVWWSZKMK2V4X3XFQYSGYCJH6LI4Q/inner/5"


def test_nested_inners_from_indexer(
    mainnet: AlgorandClient, module_snapshot: SnapshotAssertion
) -> None:
    txns = get_subscribed_transactions_for_test(
        sub.TransactionSubscriptionParams(
            filters=[
                sub.NamedTransactionFilter(
                    name="default",
                    filter=sub.TransactionFilter(
                        app_id=NESTED_INNER_APP,
                        sender="AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                    ),
                )
            ],
            max_rounds_to_sync=1,
            current_round=NESTED_INNER_ROUND + 1,
            sync_behaviour="catchup-with-indexer",
            watermark=NESTED_INNER_ROUND - 1,
        ),
        algorand=mainnet,
    )

    assert len(txns.subscribed_transactions) == 1
    assert txns.subscribed_transactions[0].id_ == NESTED_INNER_ID

    txn = txns.subscribed_transactions[0]
    assert module_snapshot == txn


def test_nested_inners_from_algod(
    mainnet: AlgorandClient, module_snapshot: SnapshotAssertion
) -> None:
    txns = get_subscribed_transactions_for_test(
        sub.TransactionSubscriptionParams(
            filters=[
                sub.NamedTransactionFilter(
                    name="default",
                    filter=sub.TransactionFilter(
                        app_id=NESTED_INNER_APP,
                        sender="AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                    ),
                )
            ],
            max_rounds_to_sync=1,
            current_round=NESTED_INNER_ROUND + 1,
            sync_behaviour="sync-oldest",
            watermark=NESTED_INNER_ROUND - 1,
        ),
        algorand=mainnet,
    )

    assert len(txns.subscribed_transactions) == 1
    assert txns.subscribed_transactions[0].id_ == NESTED_INNER_ID

    txn = txns.subscribed_transactions[0]
    assert module_snapshot == txn
