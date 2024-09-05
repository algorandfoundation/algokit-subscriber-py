import pytest
from algokit_utils.beta.algorand_client import AlgorandClient
from algokit_subscriber_py.types.transaction import TransactionType

from .transactions import get_subscribed_transactions_for_test

STPF_ROUND = 35600004
STPF_TXN_ID = "G2U5DWQRQV7EGQDAHH62EDY22VYPP4VWM3V2S5BLDNXNWFNKRXMQ"

@pytest.fixture()
def algorand_mainnet() -> AlgorandClient:
    return AlgorandClient.main_net()

def test_stpf_from_indexer(algorand_mainnet: AlgorandClient) -> None:
    txns = get_subscribed_transactions_for_test(
        sub_info={
            "filters": [{
                "name": "default",
                "filter": {
                    "type": TransactionType.stpf.value,
                }
            }],
            "max_rounds_to_sync": 1,
            "current_round": STPF_ROUND + 1,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": STPF_ROUND - 1,
        },
        algorand=algorand_mainnet
    )

    assert len(txns["subscribed_transactions"]) == 1
    txn = txns["subscribed_transactions"][0]
    assert txn['id'] == STPF_TXN_ID

    # TODO: Perform snapshot assertion

def test_stpf_from_algod(algorand_mainnet: AlgorandClient) -> None:
    txns = get_subscribed_transactions_for_test(
        sub_info={
            "filters": [{
                "name": "default",
                "filter": {
                    "type": TransactionType.stpf.value,
                }
            }],
            "max_rounds_to_sync": 1,
            "current_round": STPF_ROUND,
            "sync_behaviour": "sync-oldest",
            "watermark": STPF_ROUND - 1,
        },
        algorand=algorand_mainnet
    )

    assert len(txns["subscribed_transactions"]) == 1
    txn = txns["subscribed_transactions"][0]
    assert txn['id'] == STPF_TXN_ID

    # TODO: Perform snapshot assertion
   