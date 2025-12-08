from algokit_utils import AlgorandClient

from .accounts import generate_account
from .conftest import wait_for_txn
from .transactions import get_subscribe_transactions_from_sender, send_x_transactions


def test_start_to_now(localnet: AlgorandClient) -> None:
    test_account = generate_account(localnet, 3_000_000)
    send_x_transactions(1, generate_account(localnet, 3_000_000), localnet)
    result = send_x_transactions(1, test_account, localnet)
    last_txn_round = result.last_txn_round
    txns = result.txns

    subscribed = get_subscribe_transactions_from_sender(
        localnet,
        test_account,
        sync_behaviour="catchup-with-indexer",
        max_rounds_to_sync=1,
    )

    assert subscribed.current_round == last_txn_round
    assert subscribed.starting_watermark == 0
    assert subscribed.new_watermark == last_txn_round
    assert subscribed.synced_round_range == (1, last_txn_round)
    assert len(subscribed.subscribed_transactions) == 1
    assert subscribed.subscribed_transactions[0].id_ == txns[0].tx_id


def test_max_indexer_rounds_to_sync(localnet: AlgorandClient) -> None:
    test_account = generate_account(localnet, 3_000_000)
    random_account = generate_account(localnet, 3_000_000)
    result = send_x_transactions(1, random_account, localnet)
    initial_watermark = result.last_txn_round

    txns = send_x_transactions(5, test_account, localnet)
    tx_ids = txns.tx_ids
    result = send_x_transactions(1, random_account, localnet)
    last_txn_round = result.last_txn_round

    wait_for_txn(localnet.client.indexer, result.tx_ids[0])

    expected_new_watermark = txns.rounds[2] - 1
    indexer_rounds_to_sync = expected_new_watermark - initial_watermark

    subscribed = get_subscribe_transactions_from_sender(
        localnet,
        test_account,
        sync_behaviour="catchup-with-indexer",
        max_rounds_to_sync=1,
        max_indexer_rounds_to_sync=indexer_rounds_to_sync,
        watermark=initial_watermark,
    )

    assert subscribed.current_round == last_txn_round
    assert subscribed.starting_watermark == initial_watermark
    assert subscribed.new_watermark == expected_new_watermark
    assert subscribed.synced_round_range == (
        initial_watermark + 1,
        expected_new_watermark,
    )
    assert len(subscribed.subscribed_transactions) == 2
    assert subscribed.subscribed_transactions[0].id_ == tx_ids[0]
    assert subscribed.subscribed_transactions[1].id_ == tx_ids[1]


def test_process_all_txns_with_early_start(localnet: AlgorandClient) -> None:
    test_account = generate_account(localnet, 3_000_000)
    result = send_x_transactions(2, test_account, localnet)
    older_txn_round = result.last_txn_round
    txns = result.txns
    result = send_x_transactions(1, test_account, localnet)
    current_round = result.last_txn_round
    last_tx_id = result.tx_ids[0]

    wait_for_txn(localnet.client.indexer, last_tx_id)

    subscribed = get_subscribe_transactions_from_sender(
        localnet,
        test_account,
        sync_behaviour="catchup-with-indexer",
        max_rounds_to_sync=1,
        watermark=older_txn_round - 1,
    )

    assert subscribed.current_round == current_round
    assert subscribed.starting_watermark == older_txn_round - 1
    assert subscribed.new_watermark == current_round
    assert subscribed.synced_round_range == (older_txn_round, current_round)
    assert len(subscribed.subscribed_transactions) == 2
    assert subscribed.subscribed_transactions[0].id_ == txns[1].tx_id
    assert subscribed.subscribed_transactions[1].id_ == last_tx_id


def test_historic_txns_with_indexer_and_algod(localnet: AlgorandClient) -> None:
    test_account = generate_account(localnet, 3_000_000)
    result = send_x_transactions(3, test_account, localnet)
    tx_ids = result.tx_ids
    last_txn_round = result.last_txn_round

    wait_for_txn(localnet.client.indexer, tx_ids[2])

    subscribed = get_subscribe_transactions_from_sender(
        localnet,
        test_account,
        sync_behaviour="catchup-with-indexer",
        max_rounds_to_sync=1,
    )

    assert subscribed.current_round == last_txn_round
    assert subscribed.starting_watermark == 0
    assert subscribed.new_watermark == last_txn_round
    assert subscribed.synced_round_range == (1, last_txn_round)
    assert len(subscribed.subscribed_transactions) == 3
    assert subscribed.subscribed_transactions[0].id_ == tx_ids[0]
    assert subscribed.subscribed_transactions[1].id_ == tx_ids[1]
    assert subscribed.subscribed_transactions[2].id_ == tx_ids[2]
