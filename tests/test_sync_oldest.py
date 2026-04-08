from algokit_utils import AlgorandClient

from .accounts import generate_account
from .transactions import get_subscribe_transactions_from_sender, send_x_transactions


def test_only_processes_first_chain_round_when_starting_from_beginning(
    localnet: AlgorandClient,
) -> None:
    test_account = generate_account(localnet)
    other_account = generate_account(localnet)

    # Ensure that if we are at round 0 there is a different transaction that won't be synced
    send_x_transactions(1, other_account, localnet)
    result = send_x_transactions(1, test_account, localnet)
    last_txn_round = result.last_txn_round

    subscribed = get_subscribe_transactions_from_sender(
        localnet,
        test_account,
        sync_behaviour="sync-oldest",
        max_rounds_to_sync=1,
    )

    assert subscribed.current_round == last_txn_round
    assert subscribed.starting_watermark == 0
    assert subscribed.new_watermark == 1
    assert subscribed.synced_round_range == (1, 1)
    assert len(subscribed.subscribed_transactions) == 0


def test_only_processes_first_transaction_after_watermark(localnet: AlgorandClient) -> None:
    test_account = generate_account(localnet)

    older_result = send_x_transactions(2, test_account, localnet)
    older_txn_round = older_result.last_txn_round
    txns = older_result.txns

    current_result = send_x_transactions(1, test_account, localnet)
    current_round = current_result.last_txn_round

    subscribed = get_subscribe_transactions_from_sender(
        localnet,
        test_account,
        sync_behaviour="sync-oldest",
        max_rounds_to_sync=1,
        watermark=older_txn_round - 1,
    )

    assert subscribed.current_round == current_round
    assert subscribed.starting_watermark == older_txn_round - 1
    assert subscribed.new_watermark == older_txn_round
    assert subscribed.synced_round_range == (older_txn_round, older_txn_round)
    assert len(subscribed.subscribed_transactions) == 1
    assert subscribed.subscribed_transactions[0].id_ == txns[1].tx_id


def test_process_multiple_transactions(localnet: AlgorandClient) -> None:
    test_account = generate_account(localnet)

    result = send_x_transactions(3, test_account, localnet)
    txns = result.txns
    last_txn_round = result.last_txn_round
    rounds = result.rounds

    subscribed = get_subscribe_transactions_from_sender(
        localnet,
        test_account,
        sync_behaviour="sync-oldest",
        max_rounds_to_sync=rounds[1] - rounds[0] + 1,
        watermark=rounds[0] - 1,
    )

    assert subscribed.current_round == last_txn_round
    assert subscribed.starting_watermark == rounds[0] - 1
    assert subscribed.new_watermark == rounds[1]
    assert subscribed.synced_round_range == (rounds[0], rounds[1])
    assert len(subscribed.subscribed_transactions) == 2
    assert subscribed.subscribed_transactions[0].id_ == txns[0].tx_id
    assert subscribed.subscribed_transactions[1].id_ == txns[1].tx_id
