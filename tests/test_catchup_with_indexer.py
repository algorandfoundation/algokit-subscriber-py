import time

from algokit_utils.beta.algorand_client import AlgorandClient

from .accounts import generate_account
from .transactions import get_subscribe_transactions_from_sender, send_x_transactions


def test_start_to_now() -> None:
    localnet = AlgorandClient.default_local_net()
    test_account = generate_account(localnet, 3_000_000)
    send_x_transactions(1, generate_account(localnet, 3_000_000), localnet)
    result = send_x_transactions(1, test_account, localnet)
    last_txn_round = result["last_txn_round"]
    txns = result["txns"]

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": 0,
            "current_round": last_txn_round,
        },
        test_account,
        localnet,
    )

    assert subscribed["current_round"] == last_txn_round
    assert subscribed["starting_watermark"] == 0
    assert subscribed["new_watermark"] == last_txn_round
    assert subscribed["synced_round_range"] == (1, last_txn_round)
    assert len(subscribed["subscribed_transactions"]) == 1
    assert subscribed["subscribed_transactions"][0]["id"] == txns[0]["tx_id"]


def test_max_indexer_rounds_to_sync() -> None:
    localnet = AlgorandClient.default_local_net()
    test_account = generate_account(localnet, 3_000_000)
    random_account = generate_account(localnet, 3_000_000)
    result = send_x_transactions(1, random_account, localnet)
    initial_watermark = result["last_txn_round"]

    txns = send_x_transactions(5, test_account, localnet)["txns"]
    result = send_x_transactions(1, random_account, localnet)
    last_txn_round = result["last_txn_round"]

    while True:
        try:
            localnet.client.indexer.transaction(result["tx_ids"][0])
            break
        except Exception:
            time.sleep(0.25)

    expected_new_watermark = txns[2]["confirmation"]["confirmed-round"] - 1
    indexer_rounds_to_sync = expected_new_watermark - initial_watermark

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "max_indexer_rounds_to_sync": indexer_rounds_to_sync,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": initial_watermark,
            "current_round": last_txn_round,
        },
        test_account,
        localnet,
    )

    assert subscribed["current_round"] == last_txn_round
    assert subscribed["starting_watermark"] == initial_watermark
    assert subscribed["new_watermark"] == expected_new_watermark
    assert subscribed["synced_round_range"] == (
        initial_watermark + 1,
        expected_new_watermark,
    )
    assert len(subscribed["subscribed_transactions"]) == 2
    assert subscribed["subscribed_transactions"][0]["id"] == txns[0]["tx_id"]
    assert subscribed["subscribed_transactions"][1]["id"] == txns[1]["tx_id"]


def test_process_all_txns_with_early_start() -> None:
    localnet = AlgorandClient.default_local_net()
    test_account = generate_account(localnet, 3_000_000)
    result = send_x_transactions(2, test_account, localnet)
    older_txn_round = result["last_txn_round"]
    txns = result["txns"]
    result = send_x_transactions(1, test_account, localnet)
    current_round = result["last_txn_round"]
    last_txns = result["txns"]

    while True:
        try:
            localnet.client.indexer.transaction(last_txns[0]["tx_id"])
            break
        except Exception:
            time.sleep(0.25)

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": older_txn_round - 1,
            "current_round": current_round,
        },
        test_account,
        localnet,
    )

    assert subscribed["current_round"] == current_round
    assert subscribed["starting_watermark"] == older_txn_round - 1
    assert subscribed["new_watermark"] == current_round
    assert subscribed["synced_round_range"] == (older_txn_round, current_round)
    assert len(subscribed["subscribed_transactions"]) == 2
    assert subscribed["subscribed_transactions"][0]["id"] == txns[1]["tx_id"]
    assert subscribed["subscribed_transactions"][1]["id"] == last_txns[0]["tx_id"]


def test_historic_txns_with_indexer_and_algod() -> None:
    localnet = AlgorandClient.default_local_net()
    test_account = generate_account(localnet, 3_000_000)
    result = send_x_transactions(3, test_account, localnet)
    txns = result["txns"]
    last_txn_round = result["last_txn_round"]

    while True:
        try:
            localnet.client.indexer.transaction(result["tx_ids"][2])
            break
        except Exception:
            time.sleep(0.25)

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": 0,
            "current_round": last_txn_round,
        },
        test_account,
        localnet,
    )

    assert subscribed["current_round"] == last_txn_round
    assert subscribed["starting_watermark"] == 0
    assert subscribed["new_watermark"] == last_txn_round
    assert subscribed["synced_round_range"] == (1, last_txn_round)
    assert len(subscribed["subscribed_transactions"]) == 3
    assert subscribed["subscribed_transactions"][0]["id"] == txns[0]["tx_id"]
    assert subscribed["subscribed_transactions"][1]["id"] == txns[1]["tx_id"]
    assert subscribed["subscribed_transactions"][2]["id"] == txns[2]["tx_id"]
