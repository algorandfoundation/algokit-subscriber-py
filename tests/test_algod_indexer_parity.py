import dataclasses
from unittest.mock import MagicMock

import pytest
from algokit_utils import AlgorandClient

import algokit_subscriber as sub
from tests.conftest import dataclass_to_json


@pytest.mark.parametrize(
    "start_round",
    [
        0,
        1,
        3395482,  # afrz
        3031633,  # keyreg
        10000000,
        24098947,
        35600004,
        50000005,  # acfg, appl, axfer, pay, stpf
        50000103,  # hb
        50002814,  # keyreg
        55240407,
    ],
)
def test_algo_indexer_parity(mainnet: AlgorandClient, start_round: int) -> None:
    subscription = sub.TransactionSubscriptionParams(
        filters=[sub.NamedTransactionFilter(name="all", filter=sub.TransactionFilter())],
        watermark=max(start_round - 1, 0),
        max_rounds_to_sync=1,
        max_indexer_rounds_to_sync=1,
        sync_behaviour="sync-oldest",
        current_round=mainnet.client.algod.status().last_round,
    )
    algod_response = sub.get_subscribed_transactions(
        subscription,
        algod=mainnet.client.algod,
    )
    # block_metadata is only produced for algod, so exclude from this comparison
    algod_response.block_metadata = []

    indexer_response = sub.get_subscribed_transactions(
        dataclasses.replace(subscription, sync_behaviour="catchup-with-indexer"),
        algod=MagicMock(),  # fake algod to ensure it is not used at all
        indexer=mainnet.client.indexer,
    )

    assert dataclass_to_json(algod_response) == dataclass_to_json(indexer_response)
