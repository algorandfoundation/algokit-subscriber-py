import pytest
from algokit_utils.beta.algorand_client import AlgorandClient

from .accounts import generate_account
from .transactions import get_subscribe_transactions_from_sender, send_x_transactions


@pytest.fixture()
def algorand() -> AlgorandClient:
    return AlgorandClient.default_local_net()


def test_processes_current_round_when_starting_from_beginning(algorand: AlgorandClient):
    test_account = generate_account(algorand)

    result = send_x_transactions(2, test_account, algorand)
    txns = result["txns"]
    last_txn_round = result["last_txn_round"]

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "sync_behaviour": "sync-oldest-start-now",
            "watermark": 0,
            "current_round": last_txn_round,
        },
        test_account,
        algorand,
    )

    assert subscribed["current_round"] == last_txn_round
    assert subscribed["starting_watermark"] == 0
    assert subscribed["new_watermark"] == last_txn_round
    assert subscribed["synced_round_range"] == (last_txn_round, last_txn_round)
    assert len(subscribed["subscribed_transactions"]) == 1
    assert subscribed["subscribed_transactions"][0]["id"] == txns[1]["tx_id"]


def test_only_processes_first_transaction_after_watermark(algorand: AlgorandClient):
    test_account = generate_account(algorand)

    older_result = send_x_transactions(2, test_account, algorand)
    older_txn_round = older_result["last_txn_round"]
    txns = older_result["txns"]

    current_result = send_x_transactions(1, test_account, algorand)
    current_round = current_result["last_txn_round"]

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "sync_behaviour": "sync-oldest",
            "watermark": older_txn_round - 1,
            "current_round": current_round,
        },
        test_account,
        algorand,
    )

    assert subscribed["current_round"] == current_round
    assert subscribed["starting_watermark"] == older_txn_round - 1
    assert subscribed["new_watermark"] == older_txn_round
    assert subscribed["synced_round_range"] == (older_txn_round, older_txn_round)
    assert len(subscribed["subscribed_transactions"]) == 1
    assert subscribed["subscribed_transactions"][0]["id"] == txns[1]["tx_id"]


def test_process_multiple_transactions(algorand: AlgorandClient):
    test_account = generate_account(algorand)

    result = send_x_transactions(3, test_account, algorand)
    txns = result["txns"]
    last_txn_round = result["last_txn_round"]
    rounds = result["rounds"]

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": rounds[1] - rounds[0] + 1,
            "sync_behaviour": "sync-oldest-start-now",
            "watermark": rounds[0] - 1,
            "current_round": last_txn_round,
        },
        test_account,
        algorand,
    )

    assert subscribed["current_round"] == last_txn_round
    assert subscribed["starting_watermark"] == rounds[0] - 1
    assert subscribed["new_watermark"] == rounds[1]
    assert subscribed["synced_round_range"] == (rounds[0], rounds[1])
    assert len(subscribed["subscribed_transactions"]) == 2
    assert subscribed["subscribed_transactions"][0]["id"] == txns[0]["tx_id"]
    assert subscribed["subscribed_transactions"][1]["id"] == txns[1]["tx_id"]
