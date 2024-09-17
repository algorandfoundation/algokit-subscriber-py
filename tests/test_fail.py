from algokit_utils.beta.algorand_client import AlgorandClient

from .transactions import get_subscribe_transactions_from_sender, send_x_transactions


def test_fails_if_too_far_from_tip() -> None:
    algorand: AlgorandClient = AlgorandClient.default_local_net()
    last_txn_round = send_x_transactions(
        2, algorand.account.dispenser().address, algorand
    )["last_txn_round"]

    fail_message = ""
    try:
        get_subscribe_transactions_from_sender(
            {
                "max_rounds_to_sync": 1,
                "sync_behaviour": "fail",
                "watermark": 0,
                "current_round": last_txn_round,
            },
            algorand.account.dispenser().address,
            algorand,
        )
    except Exception as e:
        fail_message = str(e)

    assert (
        fail_message
        == f"Invalid round number to subscribe from 1; current round number is {last_txn_round}"
    )


def test_does_not_fail_if_not_too_far_from_tip() -> None:
    algorand: AlgorandClient = AlgorandClient.default_local_net()
    result = send_x_transactions(2, algorand.account.dispenser().address, algorand)
    last_txn_round = result["last_txn_round"]
    txns = result["txns"]

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "sync_behaviour": "fail",
            "watermark": last_txn_round - 1,
            "current_round": last_txn_round,
        },
        algorand.account.dispenser().address,
        algorand,
    )

    assert subscribed["current_round"] == last_txn_round
    assert subscribed["starting_watermark"] == last_txn_round - 1
    assert subscribed["new_watermark"] == last_txn_round
    assert subscribed["synced_round_range"] == (last_txn_round, last_txn_round)
    assert len(subscribed["subscribed_transactions"]) == 1
    assert subscribed["subscribed_transactions"][0]["id"] == txns[1]["tx_id"]
