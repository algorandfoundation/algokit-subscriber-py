import pytest
from algokit_utils.beta.algorand_client import AlgorandClient

from .transactions import get_subscribed_transactions_for_test

NESTED_INNER_ROUND = 35214367
NESTED_INNER_APP = 1390675395
NESTED_INNER_ID = "QLYC4KMQW5RZRA7W5GYCJ4CUVWWSZKMK2V4X3XFQYSGYCJH6LI4Q/inner/5"


@pytest.fixture()
def algorand_mainnet() -> AlgorandClient:
    return AlgorandClient.main_net()

# TODO: Do a full snapshot assertion for both these tests. Just eyeballing it for now but it looks to line up with TS results

def test_nested_inners_from_indexer(algorand_mainnet: AlgorandClient) -> None:
    txns = get_subscribed_transactions_for_test(
        sub_info={
            "filters": [{
                "name": "default",
                "filter": {
                    "app_id": NESTED_INNER_APP,
                    "sender": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                }
            }],
            "rounds_to_sync": 1,
            "current_round": NESTED_INNER_ROUND + 1,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": NESTED_INNER_ROUND - 1,
        },
        algorand=algorand_mainnet
    )

    assert len(txns["subscribed_transactions"]) == 1

    # TOOD: Determine why id offset is different (off by +2)
    assert txns["subscribed_transactions"][0]['id'] == NESTED_INNER_ID

def test_nested_inners_from_algod(algorand_mainnet: AlgorandClient) -> None:
    txns = get_subscribed_transactions_for_test(
        sub_info={
            "filters": [{
                "name": "default",
                "filter": {
                    "app_id": NESTED_INNER_APP,
                    "sender": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                }
            }],
            "rounds_to_sync": 1,
            "current_round": NESTED_INNER_ROUND + 1,
            "sync_behaviour": "sync-oldest",
            "watermark": NESTED_INNER_ROUND - 1,
        },
        algorand=algorand_mainnet
    )

    assert len(txns["subscribed_transactions"]) == 1

    # TOOD: Determine why id offset is different (off by +1)
    assert txns["subscribed_transactions"][0]['id'] == NESTED_INNER_ID
