from algokit_utils import AlgorandClient

from algokit_subscriber.types import subscription as sub

from .accounts import generate_account
from .conftest import wait_for_round
from .transactions import get_subscribed_transactions_for_test, send_x_transactions


def test_multiple_filters_with_indexer() -> None:
    localnet = AlgorandClient.default_localnet()
    localnet.set_default_validity_window(1000)
    senders = [
        generate_account(localnet),
        generate_account(localnet),
        generate_account(localnet),
    ]

    tx_ids1 = send_x_transactions(2, senders[0], localnet).tx_ids
    tx_ids2 = send_x_transactions(2, senders[1], localnet).tx_ids
    tx_ids3 = send_x_transactions(2, senders[2], localnet).tx_ids
    post_indexer_round = send_x_transactions(
        1, generate_account(localnet), localnet
    ).last_txn_round
    tx_ids11 = send_x_transactions(1, senders[0], localnet).tx_ids
    tx_ids22 = send_x_transactions(1, senders[1], localnet).tx_ids
    tx_ids33 = send_x_transactions(1, senders[2], localnet).tx_ids
    last_txn_round = send_x_transactions(1, generate_account(localnet), localnet).last_txn_round
    wait_for_round(localnet.client.indexer, last_txn_round)

    subscribed = get_subscribed_transactions_for_test(
        sub.TransactionSubscriptionParams(
            filters=[
                sub.NamedTransactionFilter(
                    name="default", filter=sub.TransactionFilter(sender=senders)
                ),
            ],
            max_rounds_to_sync=last_txn_round - post_indexer_round,
            sync_behaviour="catchup-with-indexer",
            current_round=last_txn_round,
            watermark=0,
        ),
        localnet,
    )

    assert subscribed.current_round == last_txn_round
    assert subscribed.starting_watermark == 0
    assert subscribed.new_watermark == last_txn_round
    assert subscribed.synced_round_range == (1, last_txn_round)
    assert len(subscribed.subscribed_transactions) == 9
    assert subscribed.subscribed_transactions[0].id_ == tx_ids1[0]
    assert subscribed.subscribed_transactions[1].id_ == tx_ids1[1]
    assert subscribed.subscribed_transactions[2].id_ == tx_ids2[0]
    assert subscribed.subscribed_transactions[3].id_ == tx_ids2[1]
    assert subscribed.subscribed_transactions[4].id_ == tx_ids3[0]
    assert subscribed.subscribed_transactions[5].id_ == tx_ids3[1]
    assert subscribed.subscribed_transactions[6].id_ == tx_ids11[0]
    assert subscribed.subscribed_transactions[7].id_ == tx_ids22[0]
    assert subscribed.subscribed_transactions[8].id_ == tx_ids33[0]
