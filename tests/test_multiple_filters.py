import time

from algokit_utils.beta.algorand_client import AlgorandClient

from .accounts import generate_account
from .transactions import get_subscribed_transactions_for_test, send_x_transactions


def test_multiple_filters_with_indexer() -> None:
    algorand = AlgorandClient.default_local_net()
    algorand.set_default_validity_window(1000)
    senders = [
        generate_account(algorand),
        generate_account(algorand),
        generate_account(algorand),
    ]

    tx_ids1 = send_x_transactions(2, senders[0], algorand)["tx_ids"]
    tx_ids2 = send_x_transactions(2, senders[1], algorand)["tx_ids"]
    tx_ids3 = send_x_transactions(2, senders[2], algorand)["tx_ids"]
    post_indexer_round = send_x_transactions(1, generate_account(algorand), algorand)[
        "last_txn_round"
    ]
    tx_ids11 = send_x_transactions(1, senders[0], algorand)["tx_ids"]
    tx_ids22 = send_x_transactions(1, senders[1], algorand)["tx_ids"]
    tx_ids33 = send_x_transactions(1, senders[2], algorand)["tx_ids"]
    last_txn_round = send_x_transactions(1, generate_account(algorand), algorand)[
        "last_txn_round"
    ]
    while True:
        try:
            algorand.client.indexer.block_info(last_txn_round)
            break
        except Exception:
            time.sleep(1)

    subscribed = get_subscribed_transactions_for_test(
        {
            "filters": [
                {
                    "name": "default",
                    "filter": {
                        "sender": senders,
                    },
                }
            ],
            "max_rounds_to_sync": last_txn_round - post_indexer_round,
            "sync_behaviour": "catchup-with-indexer",
            "current_round": last_txn_round,
            "watermark": 0,
        },
        algorand,
    )

    assert subscribed["current_round"] == last_txn_round
    assert subscribed["starting_watermark"] == 0
    assert subscribed["new_watermark"] == last_txn_round
    assert subscribed["synced_round_range"] == (1, last_txn_round)
    assert len(subscribed["subscribed_transactions"]) == 9
    assert subscribed["subscribed_transactions"][0]["id"] == tx_ids1[0]
    assert subscribed["subscribed_transactions"][1]["id"] == tx_ids1[1]
    assert subscribed["subscribed_transactions"][2]["id"] == tx_ids2[0]
    assert subscribed["subscribed_transactions"][3]["id"] == tx_ids2[1]
    assert subscribed["subscribed_transactions"][4]["id"] == tx_ids3[0]
    assert subscribed["subscribed_transactions"][5]["id"] == tx_ids3[1]
    assert subscribed["subscribed_transactions"][6]["id"] == tx_ids11[0]
    assert subscribed["subscribed_transactions"][7]["id"] == tx_ids22[0]
    assert subscribed["subscribed_transactions"][8]["id"] == tx_ids33[0]
