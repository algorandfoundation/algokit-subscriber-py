import time

from algokit_utils.beta.algorand_client import AlgorandClient

from .accounts import generate_account
from .transactions import get_subscribe_transactions_from_sender, send_x_transactions

#   test('Processes start of chain to now when starting from beginning of chain', async () => {
#     const { algod, indexer, testAccount, generateAccount, waitForIndexerTransaction } = localnet.context
#     // Ensure that if we are at round 0 there is a different transaction that won't be synced
#     await SendXTransactions(1, await generateAccount({ initialFunds: (3).algos() }), algod)
#     const { lastTxnRound, txns } = await SendXTransactions(1, testAccount, algod)
#     await waitForIndexerTransaction(txns[0].transaction.txID())

#     const subscribed = await GetSubscribedTransactionsFromSender(
#       { roundsToSync: 1, syncBehaviour: 'catchup-with-indexer', watermark: 0, currentRound: lastTxnRound },
#       testAccount,
#       algod,
#       indexer,
#     )

#     expect(subscribed.currentRound).toBe(lastTxnRound)
#     expect(subscribed.startingWatermark).toBe(0)
#     expect(subscribed.newWatermark).toBe(lastTxnRound)
#     expect(subscribed.syncedRoundRange).toEqual([1, lastTxnRound])
#     expect(subscribed.subscribedTransactions.length).toBe(1)
#     expect(subscribed.subscribedTransactions[0].id).toBe(txns[0].transaction.txID())
#   })
def test_start_to_now() -> None:
    localnet = AlgorandClient.default_local_net()
    test_account = generate_account(localnet, 3_000_000)
    send_x_transactions(1, generate_account(localnet, 3_000_000), localnet)
    result = send_x_transactions(1, test_account, localnet)
    last_txn_round = result["last_txn_round"]
    txns = result["txns"]

    subscribed = get_subscribe_transactions_from_sender(
        {
            "rounds_to_sync": 1,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": 0,
            "current_round": last_txn_round
        },
        test_account,
        localnet
    )

    assert subscribed['current_round'] == last_txn_round
    assert subscribed['starting_watermark'] == 0
    assert subscribed['new_watermark'] == last_txn_round
    assert subscribed['synced_round_range'] == (1, last_txn_round)
    assert len(subscribed['subscribed_transactions']) == 1
    assert subscribed['subscribed_transactions'][0]['id'] == txns[0]['tx_id']

#   test('Limits the number of synced transactions to maxIndexerRoundsToSync', async () => {
#     const { algod, indexer, testAccount, generateAccount, waitForIndexerTransaction } = localnet.context
#     // Ensure that if we are at round 0 there is a different transaction that won't be synced
#     const randomAccount = await generateAccount({ initialFunds: (3).algos() })
#     const { lastTxnRound: initialWatermark } = await SendXTransactions(1, randomAccount, algod)
#     const { txns } = await SendXTransactions(5, testAccount, algod)
#     const { lastTxnRound, txIds } = await SendXTransactions(1, randomAccount, algod)
#     await waitForIndexerTransaction(txIds[0])
#     const expectedNewWatermark = Number(txns[2].confirmation!.confirmedRound!) - 1
#     const indexerRoundsToSync = expectedNewWatermark - initialWatermark

#     const subscribed = await GetSubscribedTransactionsFromSender(
#       {
#         roundsToSync: 1,
#         indexerRoundsToSync,
#         syncBehaviour: 'catchup-with-indexer',
#         watermark: initialWatermark,
#         currentRound: lastTxnRound,
#       },
#       testAccount,
#       algod,
#       indexer,
#     )

#     expect(subscribed.currentRound).toBe(lastTxnRound)
#     expect(subscribed.startingWatermark).toBe(initialWatermark)
#     expect(subscribed.newWatermark).toBe(expectedNewWatermark)
#     expect(subscribed.syncedRoundRange).toEqual([initialWatermark + 1, expectedNewWatermark])
#     expect(subscribed.subscribedTransactions.length).toBe(2)
#     expect(subscribed.subscribedTransactions[0].id).toBe(txns[0].transaction.txID())
#     expect(subscribed.subscribedTransactions[1].id).toBe(txns[1].transaction.txID())
#   })
def test_max_indexer_rounds_to_sync() -> None:
    localnet = AlgorandClient.default_local_net()
    test_account = generate_account(localnet, 3_000_000)
    random_account = generate_account(localnet, 3_000_000)
    result = send_x_transactions(1, random_account, localnet)
    initial_watermark = result['last_txn_round']

    txns = send_x_transactions(5, test_account, localnet)['txns']
    result = send_x_transactions(1, random_account, localnet)
    last_txn_round = result['last_txn_round']

    while True:
        try:
            localnet.client.indexer.transaction(result['tx_ids'][0])
            break
        except Exception:
            time.sleep(0.25)

    expected_new_watermark = txns[2]['confirmation']['confirmed-round'] - 1
    indexer_rounds_to_sync = expected_new_watermark - initial_watermark

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "max_indexer_rounds_to_sync": indexer_rounds_to_sync,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": initial_watermark,
            "current_round": last_txn_round
        },
        test_account,
        localnet
    )

    assert subscribed['current_round'] == last_txn_round
    assert subscribed['starting_watermark'] == initial_watermark
    assert subscribed['new_watermark'] == expected_new_watermark
    assert subscribed['synced_round_range'] == (initial_watermark + 1, expected_new_watermark)
    assert len(subscribed['subscribed_transactions']) == 2
    assert subscribed['subscribed_transactions'][0]['id'] == txns[0]['tx_id']
    assert subscribed['subscribed_transactions'][1]['id'] == txns[1]['tx_id']

#   test('Processes all transactions after watermark when starting from an earlier round with other transactions', async () => {
#     const { algod, indexer, testAccount, waitForIndexerTransaction } = localnet.context
#     const { txns, lastTxnRound: olderTxnRound } = await SendXTransactions(2, testAccount, algod)
#     const { lastTxnRound: currentRound, txns: lastTxns } = await SendXTransactions(1, testAccount, algod)
#     await waitForIndexerTransaction(lastTxns[0].transaction.txID())

#     const subscribed = await GetSubscribedTransactionsFromSender(
#       { roundsToSync: 1, syncBehaviour: 'catchup-with-indexer', watermark: olderTxnRound - 1, currentRound },
#       testAccount,
#       algod,
#       indexer,
#     )

#     expect(subscribed.currentRound).toBe(currentRound)
#     expect(subscribed.startingWatermark).toBe(olderTxnRound - 1)
#     expect(subscribed.newWatermark).toBe(currentRound)
#     expect(subscribed.syncedRoundRange).toEqual([olderTxnRound, currentRound])
#     expect(subscribed.subscribedTransactions.length).toBe(2)
#     expect(subscribed.subscribedTransactions[0].id).toBe(txns[1].transaction.txID())
#     expect(subscribed.subscribedTransactions[1].id).toBe(lastTxns[0].transaction.txID())
#   })
def test_process_all_txns_with_early_start() -> None:
    localnet = AlgorandClient.default_local_net()
    test_account = generate_account(localnet, 3_000_000)
    result = send_x_transactions(2, test_account, localnet)
    older_txn_round = result['last_txn_round']
    txns = result['txns']
    result = send_x_transactions(1, test_account, localnet)
    current_round = result['last_txn_round']
    last_txns = result['txns']

    while True:
        try:
            localnet.client.indexer.transaction(last_txns[0]['tx_id'])
            break
        except Exception:
            time.sleep(0.25)

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": older_txn_round - 1,
            "current_round": current_round
        },
        test_account,
        localnet
    )

    assert subscribed['current_round'] == current_round
    assert subscribed['starting_watermark'] == older_txn_round - 1
    assert subscribed['new_watermark'] == current_round
    assert subscribed['synced_round_range'] == (older_txn_round, current_round)
    assert len(subscribed['subscribed_transactions']) == 2
    assert subscribed['subscribed_transactions'][0]['id'] == txns[1]['tx_id']
    assert subscribed['subscribed_transactions'][1]['id'] == last_txns[0]['tx_id']

#   test('Process multiple historic transactions using indexer and blends them in with algod transaction', async () => {
#     const { algod, indexer, testAccount, waitForIndexerTransaction } = localnet.context
#     const { txns, txIds, lastTxnRound } = await SendXTransactions(3, testAccount, algod)
#     await waitForIndexerTransaction(txIds[2])

#     const subscribed = await GetSubscribedTransactionsFromSender(
#       { roundsToSync: 1, syncBehaviour: 'catchup-with-indexer', watermark: 0, currentRound: lastTxnRound },
#       testAccount,
#       algod,
#       indexer,
#     )

#     expect(subscribed.currentRound).toBe(lastTxnRound)
#     expect(subscribed.startingWatermark).toBe(0)
#     expect(subscribed.newWatermark).toBe(lastTxnRound)
#     expect(subscribed.syncedRoundRange).toEqual([1, lastTxnRound])
#     expect(subscribed.subscribedTransactions.length).toBe(3)
#     expect(subscribed.subscribedTransactions[0].id).toBe(txns[0].transaction.txID())
#     expect(subscribed.subscribedTransactions[1].id).toBe(txns[1].transaction.txID())
#     expect(subscribed.subscribedTransactions[2].id).toBe(txns[2].transaction.txID())
#   })
def test_historic_txns_with_indexer_and_algod() -> None:
    localnet = AlgorandClient.default_local_net()
    test_account = generate_account(localnet, 3_000_000)
    result = send_x_transactions(3, test_account, localnet)
    txns = result['txns']
    last_txn_round = result['last_txn_round']

    while True:
        try:
            localnet.client.indexer.transaction(result['tx_ids'][2])
            break
        except Exception:
            time.sleep(0.25)

    subscribed = get_subscribe_transactions_from_sender(
        {
            "max_rounds_to_sync": 1,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": 0,
            "current_round": last_txn_round
        },
        test_account,
        localnet
    )

    assert subscribed['current_round'] == last_txn_round
    assert subscribed['starting_watermark'] == 0
    assert subscribed['new_watermark'] == last_txn_round
    assert subscribed['synced_round_range'] == (1, last_txn_round)
    assert len(subscribed['subscribed_transactions']) == 3
    assert subscribed['subscribed_transactions'][0]['id'] == txns[0]['tx_id']
    assert subscribed['subscribed_transactions'][1]['id'] == txns[1]['tx_id']
    assert subscribed['subscribed_transactions'][2]['id'] == txns[2]['tx_id']
