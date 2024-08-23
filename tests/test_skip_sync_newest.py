from algokit_utils.beta.algorand_client import AlgorandClient

from .accounts import generate_account
from .transactions import get_subscribe_transactions_from_sender, send_x_transactions

#  test('Only processes the latest transaction when starting from beginning of chain', async () => {
#     const { algod, testAccount } = localnet.context
#     const { txns, lastTxnRound } = await SendXTransactions(2, testAccount, algod)

#     const subscribed = await GetSubscribedTransactionsFromSender(
#       { roundsToSync: 1, syncBehaviour: 'skip-sync-newest', watermark: 0, currentRound: lastTxnRound },
#       testAccount,
#       algod,
#     )

#     expect(subscribed.currentRound).toBe(lastTxnRound)
#     expect(subscribed.startingWatermark).toBe(0)
#     expect(subscribed.newWatermark).toBe(lastTxnRound)
#     expect(subscribed.syncedRoundRange).toEqual([lastTxnRound, lastTxnRound])
#     expect(subscribed.subscribedTransactions.length).toBe(1)
#     expect(subscribed.subscribedTransactions[0].id).toBe(txns[1].transaction.txID())
#   })
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
    assert subscribed["subscribed_transactions"][0]["id"] == txns[1]['tx_id']

#   test('Only processes the latest transaction when starting from an earlier round with other transactions', async () => {
#     const { algod, testAccount } = localnet.context
#     const { lastTxnRound: olderTxnRound } = await SendXTransactions(2, testAccount, algod)
#     const { txns, lastTxnRound: currentRound } = await SendXTransactions(1, testAccount, algod)

#     const subscribed = await GetSubscribedTransactionsFromSender(
#       { roundsToSync: 1, syncBehaviour: 'skip-sync-newest', watermark: olderTxnRound - 1, currentRound },
#       testAccount,
#       algod,
#     )

#     expect(subscribed.currentRound).toBe(currentRound)
#     expect(subscribed.startingWatermark).toBe(olderTxnRound - 1)
#     expect(subscribed.newWatermark).toBe(currentRound)
#     expect(subscribed.syncedRoundRange).toEqual([currentRound, currentRound])
#     expect(subscribed.subscribedTransactions.length).toBe(1)
#     expect(subscribed.subscribedTransactions[0].id).toBe(txns[0].transaction.txID())
#   })
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
    assert subscribed["subscribed_transactions"][0]["id"] == txns[0]['tx_id']


#   test('Process multiple transactions', async () => {
#     const { algod, testAccount } = localnet.context
#     const { txns, lastTxnRound, rounds } = await SendXTransactions(3, testAccount, algod)

#     const subscribed = await GetSubscribedTransactionsFromSender(
#       { roundsToSync: lastTxnRound - rounds[1] + 1, syncBehaviour: 'skip-sync-newest', watermark: 0, currentRound: lastTxnRound },
#       testAccount,
#       algod,
#     )

#     expect(subscribed.currentRound).toBe(lastTxnRound)
#     expect(subscribed.startingWatermark).toBe(0)
#     expect(subscribed.newWatermark).toBe(lastTxnRound)
#     expect(subscribed.syncedRoundRange).toEqual([rounds[1], lastTxnRound])
#     expect(subscribed.subscribedTransactions.length).toBe(2)
#     expect(subscribed.subscribedTransactions[0].id).toBe(txns[1].transaction.txID())
#     expect(subscribed.subscribedTransactions[1].id).toBe(txns[2].transaction.txID())
#   })
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
    assert subscribed["subscribed_transactions"][0]["id"] == txns[1]['tx_id']
    assert subscribed["subscribed_transactions"][1]["id"] == txns[2]['tx_id']
