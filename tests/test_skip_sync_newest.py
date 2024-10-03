from algokit_utils.beta.algorand_client import AlgorandClient

from .accounts import generate_account
from .transactions import get_subscribe_transactions_from_sender, send_x_transactions


def test_only_processes_latest_txn() -> None:
    algorand = AlgorandClient.default_local_net()
    test_account = generate_account(algorand)

    results = send_x_transactions(2, test_account, algorand)
    last_txn_round = results["last_txn_round"]
    txns = results["txns"]

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "sync_behaviour": "skip-sync-newest",
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


def test_only_processes_latest_txn_with_earlier_round_start() -> None:
    algorand = AlgorandClient.default_local_net()
    test_account = generate_account(algorand)

    older_txn_results = send_x_transactions(2, test_account, algorand)
    older_txn_round = older_txn_results["last_txn_round"]

    current_txn_results = send_x_transactions(1, test_account, algorand)
    current_txn_round = current_txn_results["last_txn_round"]
    txns = current_txn_results["txns"]

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "sync_behaviour": "skip-sync-newest",
            "watermark": older_txn_round - 1,
            "current_round": current_txn_round,
        },
        test_account,
        algorand,
    )

    assert subscribed["current_round"] == current_txn_round
    assert subscribed["starting_watermark"] == older_txn_round - 1
    assert subscribed["new_watermark"] == current_txn_round
    assert subscribed["synced_round_range"] == (current_txn_round, current_txn_round)
    assert len(subscribed["subscribed_transactions"]) == 1
    assert subscribed["subscribed_transactions"][0]["id"] == txns[0]["tx_id"]


def test_process_multiple_txns() -> None:
    algorand = AlgorandClient.default_local_net()
    test_account = generate_account(algorand)

    results = send_x_transactions(3, test_account, algorand)
    last_txn_round = results["last_txn_round"]
    txns = results["txns"]
    rounds = results["rounds"]

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": last_txn_round - rounds[1] + 1,
            "sync_behaviour": "skip-sync-newest",
            "watermark": 0,
            "current_round": last_txn_round,
        },
        test_account,
        algorand,
    )

    assert subscribed["current_round"] == last_txn_round
    assert subscribed["starting_watermark"] == 0
    assert subscribed["new_watermark"] == last_txn_round
    assert subscribed["synced_round_range"] == (rounds[1], last_txn_round)
    assert len(subscribed["subscribed_transactions"]) == 2
    assert subscribed["subscribed_transactions"][0]["id"] == txns[1]["tx_id"]
    assert subscribed["subscribed_transactions"][1]["id"] == txns[2]["tx_id"]
