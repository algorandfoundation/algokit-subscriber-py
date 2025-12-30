from algokit_utils import AlgorandClient
from syrupy.assertion import SnapshotAssertion

from algokit_subscriber.types import subscription as sub

from .transactions import get_subscribed_transactions_for_test

KEYREG_ROUND = 34418662
KEYREG_TXN_ID = "LSTIW7IBLO4SFPLFAI45WAV3NPXYPX6RWPTZ5KYDL3NX2LTJFXNA"


def test_keyreg_from_indexer(mainnet: AlgorandClient, module_snapshot: SnapshotAssertion) -> None:
    txns = get_subscribed_transactions_for_test(
        sub.TransactionSubscriptionParams(
            filters=[
                sub.NamedTransactionFilter(
                    name="default",
                    filter=sub.TransactionFilter(
                        type="keyreg",
                        sender="HQQRVWPYAHABKCXNMZRG242Z5GWFTJMRO63HDCLF23ZWCT3IPQXIGQ2KGY",
                    ),
                )
            ],
            max_rounds_to_sync=1,
            current_round=KEYREG_ROUND + 1,
            sync_behaviour="catchup-with-indexer",
            watermark=KEYREG_ROUND - 1,
        ),
        algorand=mainnet,
    )

    assert len(txns.subscribed_transactions) == 1
    txn = txns.subscribed_transactions[0]
    # https://allo.info/tx/LSTIW7IBLO4SFPLFAI45WAV3NPXYPX6RWPTZ5KYDL3NX2LTJFXNA
    assert txn.id_ == KEYREG_TXN_ID

    assert txn == module_snapshot


def test_keyreg_from_algod(mainnet: AlgorandClient, module_snapshot: SnapshotAssertion) -> None:
    txns = get_subscribed_transactions_for_test(
        sub.TransactionSubscriptionParams(
            filters=[
                sub.NamedTransactionFilter(
                    name="default",
                    filter=sub.TransactionFilter(
                        type="keyreg",
                        sender="HQQRVWPYAHABKCXNMZRG242Z5GWFTJMRO63HDCLF23ZWCT3IPQXIGQ2KGY",
                    ),
                )
            ],
            max_rounds_to_sync=1,
            current_round=KEYREG_ROUND + 1,
            sync_behaviour="sync-oldest",
            watermark=KEYREG_ROUND - 1,
        ),
        algorand=mainnet,
    )

    assert len(txns.subscribed_transactions) == 1
    txn = txns.subscribed_transactions[0]
    # https://allo.info/tx/LSTIW7IBLO4SFPLFAI45WAV3NPXYPX6RWPTZ5KYDL3NX2LTJFXNA
    assert txn.id_ == KEYREG_TXN_ID

    assert txn == module_snapshot
