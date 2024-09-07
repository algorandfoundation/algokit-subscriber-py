import contextlib
import time

from algokit_subscriber_py.subscriber import AlgorandSubscriber
from algokit_utils.beta.algorand_client import AlgorandClient

from .accounts import generate_account
from .transactions import send_x_transactions

#   const getSubscriber = (
#     config: { testAccount: SendTransactionFrom; configOverrides?: Partial<AlgorandSubscriberConfig>; initialWatermark?: number },
#     algod: Algodv2,
#     indexer?: Indexer,
#   ) => {
#     let watermark = config.initialWatermark ?? 0
#     const subscribedTxns: string[] = []

#     const subscriber = new AlgorandSubscriber(
#       {
#         ...config.configOverrides,
#         filters: [
#           {
#             name: 'test-txn',
#             filter: {
#               sender: algokit.getSenderAddress(config.testAccount),
#             },
#           },
#           ...(config.configOverrides?.filters ?? []),
#         ],
#         syncBehaviour: config.configOverrides?.syncBehaviour ?? 'sync-oldest',
#         watermarkPersistence: InMemoryWatermark(
#           () => watermark,
#           (w) => (watermark = w),
#         ),
#       },
#       algod,
#       indexer,
#     )
#     subscriber.on('test-txn', (r) => {
#       subscribedTxns.push(r.id)
#     })
#     return {
#       subscriber,
#       subscribedTestAccountTxns: subscribedTxns,
#       getWatermark: () => watermark,
#     }
#   }
def get_subscriber(algorand: AlgorandClient, test_account: str, config_overrides: dict | None = None, initial_watermark: int = 0) -> dict:
    watermark = initial_watermark
    config_overrides = config_overrides or {}

    def get_watermark() -> int:
        return watermark

    def set_watermark(new_watermark: int) -> None:
        nonlocal watermark
        watermark = new_watermark

    subscribed_txns = []

    subscriber = AlgorandSubscriber(
        {
            **config_overrides,
            'filters': [
                {
                    'name': 'test-txn',
                    'filter': {
                        'sender': test_account,
                    },
                },
                *config_overrides.get('filters', []),
            ],
            'sync_behaviour': config_overrides.get('sync_behaviour', 'sync-oldest'),
            'watermark_persistence': {
                'set': set_watermark,
                'get': get_watermark,
            },
        },
        algorand.client.algod,
        algorand.client.indexer
    )
    subscriber.on('test-txn', lambda r, _: subscribed_txns.append(r['id']))
    return {
        'subscriber': subscriber,
        'subscribed_test_account_txns': subscribed_txns,
        'get_watermark': lambda: watermark,
    }

#   test('Subscribes to transactions correctly when controlling polling', async () => {
#     const { algod, testAccount, generateAccount } = localnet.context
#     const { lastTxnRound, txIds } = await SendXTransactions(1, testAccount, algod)
#     const {
#       subscriber,
#       subscribedTestAccountTxns: subscribedTxns,
#       getWatermark,
#     } = getSubscriber({ testAccount, initialWatermark: lastTxnRound - 1 }, algod)

#     // Initial catch up with indexer
#     const result = await subscriber.pollOnce()
#     expect(subscribedTxns.length).toBe(1)
#     expect(subscribedTxns[0]).toBe(txIds[0])
#     expect(getWatermark()).toBeGreaterThanOrEqual(lastTxnRound)
#     expect(result.currentRound).toBeGreaterThanOrEqual(lastTxnRound)
#     expect(result.startingWatermark).toBe(lastTxnRound - 1)
#     expect(result.newWatermark).toBe(result.currentRound)
#     expect(result.syncedRoundRange).toEqual([lastTxnRound, result.currentRound])
#     expect(result.subscribedTransactions.length).toBe(1)
#     expect(result.subscribedTransactions.map((t) => t.id)).toEqual(txIds)

#     // Random transaction
#     const { lastTxnRound: lastTxnRound2 } = await SendXTransactions(1, await generateAccount({ initialFunds: (3).algos() }), algod)
#     await subscriber.pollOnce()
#     expect(subscribedTxns.length).toBe(1)
#     expect(getWatermark()).toBeGreaterThanOrEqual(lastTxnRound2)

#     // Another subscribed transaction
#     const { lastTxnRound: lastTxnRound3, txIds: txIds3 } = await SendXTransactions(1, testAccount, algod)
#     await subscriber.pollOnce()
#     expect(subscribedTxns.length).toBe(2)
#     expect(subscribedTxns[1]).toBe(txIds3[0])
#     expect(getWatermark()).toBeGreaterThanOrEqual(lastTxnRound3)
#   })
def test_subscribes_correctly_with_poll_once() -> None:
    algorand = AlgorandClient.default_local_net()
    test_account = generate_account(algorand)
    results = send_x_transactions(1, test_account, algorand)
    last_txn_round = results['last_txn_round']
    tx_ids = results['tx_ids']
    subscriber = get_subscriber(algorand, test_account, initial_watermark=last_txn_round - 1)

    # Initial catch up with indexer
    result = subscriber['subscriber'].poll_once()
    assert len(subscriber['subscribed_test_account_txns']) == 1
    assert subscriber['subscribed_test_account_txns'][0] == tx_ids[0]
    assert subscriber['get_watermark']() >= last_txn_round
    assert result['current_round'] >= last_txn_round
    assert result['starting_watermark'] == last_txn_round - 1
    assert result['new_watermark'] == result['current_round']
    assert result['synced_round_range'] == (last_txn_round, result['current_round'])
    assert len(result['subscribed_transactions']) == 1
    assert [t['id'] for t in result['subscribed_transactions']] == tx_ids

    # Random transaction
    results_2 = send_x_transactions(1, generate_account(algorand, 3 * 10**6), algorand)
    last_txn_round_2 = results_2['last_txn_round']
    subscriber['subscriber'].poll_once()
    assert len(subscriber['subscribed_test_account_txns']) == 1
    assert subscriber['get_watermark']() >= last_txn_round_2

    # Another subscribed transaction
    results_3 = send_x_transactions(1, test_account, algorand)
    last_txn_round_3 = results_3['last_txn_round']
    tx_ids_3 = results_3['tx_ids']
    subscriber['subscriber'].poll_once()
    assert len(subscriber['subscribed_test_account_txns']) == 2
    assert subscriber['subscribed_test_account_txns'][1] == tx_ids_3[0]
    assert subscriber['get_watermark']() >= last_txn_round_3

# test('Subscribes to transactions with multiple filters correctly', async () => {
#     const { algod, testAccount, generateAccount } = localnet.context
#     const randomAccount = await generateAccount({ initialFunds: (3).algos() })
#     const senders = [await generateAccount({ initialFunds: (5).algos() }), await generateAccount({ initialFunds: (5).algos() })]
#     const sender1TxnIds: string[] = []
#     let sender1TxnIdsfromBatch: string[] = []
#     const sender2Rounds: number[] = []
#     let sender2RoundsfromBatch: number[] = []
#     const { lastTxnRound: firstTxnRound, txIds } = await SendXTransactions(1, testAccount, algod)
#     const { txIds: txIds1 } = await SendXTransactions(2, senders[0], algod)
#     const { lastTxnRound, txIds: txIds2, txns: txns2 } = await SendXTransactions(2, senders[1], algod)
#     const { subscriber, getWatermark } = getSubscriber(
#       {
#         testAccount,
#         initialWatermark: firstTxnRound - 1,
#         configOverrides: {
#           maxRoundsToSync: 100,
#           filters: [
#             {
#               name: 'sender1',
#               filter: {
#                 sender: algokit.getSenderAddress(senders[0]),
#               },
#               mapper: (txs) => Promise.resolve(txs.map((t) => t.id)),
#             },
#             {
#               name: 'sender2',
#               filter: {
#                 sender: algokit.getSenderAddress(senders[1]),
#               },
#               mapper: (txs) => Promise.resolve(txs.map((t) => t['confirmed-round']!)),
#             },
#           ],
#         },
#       },
#       algod,
#     )
#     subscriber.onBatch<string>('sender1', (r) => {
#       sender1TxnIdsfromBatch = r
#     })
#     subscriber.on<string>('sender1', (r) => {
#       sender1TxnIds.push(r)
#     })
#     subscriber.onBatch<number>('sender2', (r) => {
#       sender2RoundsfromBatch = r
#     })
#     subscriber.on<number>('sender2', (r) => {
#       sender2Rounds.push(r)
#     })

#     // Initial catch up
#     const result = await subscriber.pollOnce()
#     console.log(
#       `Synced ${result.subscribedTransactions.length} transactions from rounds ${result.syncedRoundRange[0]}-${result.syncedRoundRange[1]} when current round is ${result.currentRound}`,
#       result.subscribedTransactions.map((t) => t.id),
#     )
#     const subscribedTxns = result.subscribedTransactions
#     expect(subscribedTxns.length).toBe(5)
#     expect(subscribedTxns[0].id).toBe(txIds[0])
#     expect(subscribedTxns[1].id).toBe(txIds1[0])
#     expect(subscribedTxns[2].id).toBe(txIds1[1])
#     expect(subscribedTxns[3].id).toBe(txIds2[0])
#     expect(subscribedTxns[4].id).toBe(txIds2[1])
#     expect(result.currentRound).toBeGreaterThanOrEqual(lastTxnRound)
#     expect(result.startingWatermark).toBe(firstTxnRound - 1)
#     expect(result.newWatermark).toBe(result.currentRound)
#     expect(getWatermark()).toBeGreaterThanOrEqual(result.currentRound)
#     expect(result.syncedRoundRange).toEqual([firstTxnRound, result.currentRound])
#     expect(result.subscribedTransactions.length).toBe(5)
#     expect(result.subscribedTransactions.map((t) => t.id)).toEqual(txIds.concat(txIds1, txIds2))
#     expect(sender1TxnIds).toEqual(txIds1)
#     expect(sender1TxnIdsfromBatch).toEqual(sender1TxnIds)
#     expect(sender2Rounds).toEqual(txns2.map((t) => Number(t.confirmation!.confirmedRound!)))
#     expect(sender2RoundsfromBatch).toEqual(sender2Rounds)

#     // Random transaction
#     const { lastTxnRound: lastTxnRound2 } = await SendXTransactions(1, randomAccount, algod)
#     const result2 = await subscriber.pollOnce()
#     expect(result2.subscribedTransactions.length).toBe(0)
#     expect(getWatermark()).toBeGreaterThanOrEqual(lastTxnRound2)

#     // More subscribed transactions
#     const { txIds: txIds3 } = await SendXTransactions(1, testAccount, algod)
#     const { txIds: txIds13 } = await SendXTransactions(2, senders[0], algod)
#     const { lastTxnRound: lastSubscribedRound3, txIds: txIds23, txns: txns23 } = await SendXTransactions(2, senders[1], algod)

#     const result3 = await subscriber.pollOnce()
#     console.log(
#       `Synced ${result3.subscribedTransactions.length} transactions from rounds ${result3.syncedRoundRange[0]}-${result3.syncedRoundRange[1]} when current round is ${result3.currentRound}`,
#       result3.subscribedTransactions.map((t) => t.id),
#     )
#     const subscribedTxns3 = result3.subscribedTransactions
#     expect(subscribedTxns3.length).toBe(5)
#     expect(subscribedTxns3[0].id).toBe(txIds3[0])
#     expect(subscribedTxns3[1].id).toBe(txIds13[0])
#     expect(subscribedTxns3[2].id).toBe(txIds13[1])
#     expect(subscribedTxns3[3].id).toBe(txIds23[0])
#     expect(subscribedTxns3[4].id).toBe(txIds23[1])
#     expect(result3.currentRound).toBeGreaterThanOrEqual(lastSubscribedRound3)
#     expect(result3.startingWatermark).toBe(result2.newWatermark)
#     expect(result3.newWatermark).toBe(result3.currentRound)
#     expect(getWatermark()).toBeGreaterThanOrEqual(result3.currentRound)
#     expect(result3.syncedRoundRange).toEqual([result2.newWatermark + 1, result3.currentRound])
#     expect(result3.subscribedTransactions.length).toBe(5)
#     expect(result3.subscribedTransactions.map((t) => t.id)).toEqual(txIds3.concat(txIds13, txIds23))
#     expect(sender1TxnIds).toEqual(txIds1.concat(txIds13))
#     expect(sender1TxnIdsfromBatch).toEqual(txIds13)
#     expect(sender2Rounds).toEqual(
#       txns2.map((t) => Number(t.confirmation!.confirmedRound!)).concat(txns23.map((t) => Number(t.confirmation!.confirmedRound!))),
#     )
#     expect(sender2RoundsfromBatch).toEqual(txns23.map((t) => Number(t.confirmation!.confirmedRound!)))
#   })
def test_subscribes_correctly_with_multiple_filters() -> None:
    algorand = AlgorandClient.default_local_net()
    algorand.set_default_validity_window(1000)
    test_account = generate_account(algorand)
    random_account = generate_account(algorand, 3 * 10**6)
    senders = [generate_account(algorand, 5 * 10**6), generate_account(algorand, 5 * 10**6)]
    sender_1_txn_ids = []
    sender_1_txn_ids_from_batch = []
    sender_2_rounds = []
    sender_2_rounds_from_batch = []
    results = send_x_transactions(1, test_account, algorand)
    first_txn_round = results['last_txn_round']
    tx_ids = results['tx_ids']
    results_1 = send_x_transactions(2, senders[0], algorand)
    tx_ids_1 = results_1['tx_ids']
    results_2 = send_x_transactions(2, senders[1], algorand)
    last_txn_round = results_2['last_txn_round']
    tx_ids_2 = results_2['tx_ids']
    txns_2 = results_2['txns']
    subscriber = get_subscriber(
        algorand,
        test_account,
        config_overrides={
            'max_rounds_to_sync': 100,
            'filters': [
                {
                    'name': 'sender1',
                    'filter': {
                        'sender': senders[0],
                    },
                    'mapper': lambda txs: [t['id'] for t in txs],
                },
                {
                    'name': 'sender2',
                    'filter': {
                        'sender': senders[1],
                    },
                    'mapper': lambda txs: [t['confirmed-round'] for t in txs],
                },
            ],
        },
        initial_watermark=first_txn_round - 1
    )
    subscriber['subscriber'].on_batch('sender1', lambda r, _: sender_1_txn_ids_from_batch.extend(r))
    subscriber['subscriber'].on('sender1', lambda r, _: sender_1_txn_ids.append(r))
    subscriber['subscriber'].on_batch('sender2', lambda r, _: sender_2_rounds_from_batch.extend(r))
    subscriber['subscriber'].on('sender2', lambda r, _: sender_2_rounds.append(r))

    # Initial catch up
    result = subscriber['subscriber'].poll_once()
    subscribed_txns = result['subscribed_transactions']
    assert len(subscribed_txns) == 5
    assert subscribed_txns[0]['id'] == tx_ids[0]
    assert subscribed_txns[1]['id'] == tx_ids_1[0]
    assert subscribed_txns[2]['id'] == tx_ids_1[1]
    assert subscribed_txns[3]['id'] == tx_ids_2[0]
    assert subscribed_txns[4]['id'] == tx_ids_2[1]
    assert result['current_round'] >= last_txn_round
    assert result['starting_watermark'] == first_txn_round - 1
    assert result['new_watermark'] == result['current_round']
    assert subscriber['get_watermark']() >= result['current_round']
    assert result['synced_round_range'] == (first_txn_round, result['current_round'])
    assert len(result['subscribed_transactions']) == 5
    assert [t['id'] for t in result['subscribed_transactions']] == tx_ids + tx_ids_1 + tx_ids_2
    assert sender_1_txn_ids == tx_ids_1
    assert sender_1_txn_ids_from_batch == sender_1_txn_ids
    assert sender_2_rounds == [int(t['confirmation']['confirmed-round']) for t in txns_2]
    assert sender_2_rounds_from_batch == sender_2_rounds

    # Random transaction
    results_2 = send_x_transactions(1, random_account, algorand)
    sender_1_txn_ids_from_batch = []
    sender_2_rounds_from_batch = []
    result_2 = subscriber['subscriber'].poll_once()
    assert len(result_2['subscribed_transactions']) == 0
    assert subscriber['get_watermark']() >= results_2['last_txn_round']

    # More subscribed transactions
    results_3 = send_x_transactions(1, test_account, algorand)
    tx_ids_3 = results_3['tx_ids']
    results_13 = send_x_transactions(2, senders[0], algorand)
    tx_ids_13 = results_13['tx_ids']
    results_23 = send_x_transactions(2, senders[1], algorand)
    last_subscribed_round_3 = results_23['last_txn_round']
    tx_ids_23 = results_23['tx_ids']
    txns_23 = results_23['txns']

    sender_1_txn_ids_from_batch = []
    sender_2_rounds_from_batch = []
    result_3 = subscriber['subscriber'].poll_once()
    subscribed_txns_3 = result_3['subscribed_transactions']
    assert len(subscribed_txns_3) == 5
    assert subscribed_txns_3[0]['id'] == tx_ids_3[0]
    assert subscribed_txns_3[1]['id'] == tx_ids_13[0]
    assert subscribed_txns_3[2]['id'] == tx_ids_13[1]
    assert subscribed_txns_3[3]['id'] == tx_ids_23[0]
    assert subscribed_txns_3[4]['id'] == tx_ids_23[1]
    assert result_3['current_round'] >= last_subscribed_round_3
    assert result_3['starting_watermark'] == result_2['new_watermark']
    assert result_3['new_watermark'] == result_3['current_round']
    assert subscriber['get_watermark']() >= result_3['current_round']
    assert result_3['synced_round_range'] == (result_2['new_watermark'] + 1, result_3['current_round'])
    assert len(result_3['subscribed_transactions']) == 5
    assert [t['id'] for t in result_3['subscribed_transactions']] == tx_ids_3 + tx_ids_13 + tx_ids_23
    assert sender_1_txn_ids == tx_ids_1 + tx_ids_13
    assert len(sender_1_txn_ids_from_batch) == len(tx_ids_13)
    assert sender_1_txn_ids_from_batch == tx_ids_13
    assert sender_2_rounds == [int(t['confirmation']['confirmed-round']) for t in txns_2] + [int(t['confirmation']['confirmed-round']) for t in txns_23]
    assert sender_2_rounds_from_batch == [int(t['confirmation']['confirmed-round']) for t in txns_23]


# test('Subscribes to transactions at regular intervals when started and can be stopped', async () => {
#     const { algod, testAccount } = localnet.context
#     const { lastTxnRound, txIds } = await SendXTransactions(1, testAccount, algod)
#     const {
#       subscriber,
#       subscribedTestAccountTxns: subscribedTxns,
#       getWatermark,
#     } = getSubscriber(
#       { testAccount, configOverrides: { maxRoundsToSync: 1, frequencyInSeconds: 0.1 }, initialWatermark: lastTxnRound - 1 },
#       algod,
#     )
#     const roundsSynced: number[] = []

#     console.log('Starting subscriber')
#     subscriber.start((r) => roundsSynced.push(r.currentRound))

#     console.log('Waiting for ~0.5s')
#     await new Promise((resolve) => setTimeout(resolve, 500))
#     const pollCountBeforeStopping = roundsSynced.length

#     console.log('Stopping subscriber')
#     await subscriber.stop('TEST')
#     const pollCountAfterStopping = roundsSynced.length

#     // Assert
#     expect(subscribedTxns.length).toBe(1)
#     expect(subscribedTxns[0]).toBe(txIds[0])
#     expect(getWatermark()).toBeGreaterThanOrEqual(lastTxnRound)
#     // Polling frequency is 0.1s and we waited ~0.5s, LocalNet latency is low so expect 3-7 polls
#     expect(pollCountBeforeStopping).toBeGreaterThanOrEqual(3)
#     expect(pollCountBeforeStopping).toBeLessThanOrEqual(7)
#     // Expect no more than 1 extra poll after we called stop
#     expect(pollCountAfterStopping - pollCountBeforeStopping).toBeLessThanOrEqual(1)
#   })
def test_subscribes_correctly_with_regular_intervals_when_started_and_can_be_stopped() -> None:
    algorand = AlgorandClient.default_local_net()
    test_account = generate_account(algorand)
    results = send_x_transactions(1, test_account, algorand)
    last_txn_round = results['last_txn_round']
    tx_ids = results['tx_ids']
    subscriber = get_subscriber(
        algorand,
        test_account,
        config_overrides={
            'max_rounds_to_sync': 1,
            'frequency_in_seconds': 0.1,
        },
        initial_watermark=last_txn_round - 1
    )
    rounds_synced = []

    start_time = time.time()
    poll_count_before_stopping = None
    poll_count_after_stopping = None

    # Note: Because the python implementation is fully sync, we need to test this a bit differently
    def inspect(r: dict) -> None:
        rounds_synced.append(r['current_round'])
        nonlocal start_time

        # if 5 seconds have passed, stop the subscriber
        if time.time() - start_time >= 0.5:
            print('Waited for ~0.5s')
            nonlocal poll_count_before_stopping
            poll_count_before_stopping = len(rounds_synced)

            print('Stopping subscriber')
            subscriber['subscriber'].stop('TEST')
            nonlocal poll_count_after_stopping
            poll_count_after_stopping = len(rounds_synced)

    print('Starting subscriber')
    subscriber['subscriber'].start(inspect)

    # Assert
    assert len(subscriber['subscribed_test_account_txns']) == 1
    assert subscriber['subscribed_test_account_txns'][0] == tx_ids[0]
    assert subscriber['get_watermark']() >= last_txn_round
    # Polling frequency is 0.1s and we waited ~0.5s, LocalNet latency is low so expect 3-7 polls
    assert poll_count_before_stopping >= 3
    assert poll_count_before_stopping <= 7
    # Expect no more than 1 extra poll after we called stop
    assert poll_count_after_stopping - poll_count_before_stopping <= 1

# test('Waits until transaction appears by default when started', async () => {
#     const { algod, testAccount } = localnet.context
#     const currentRound = (await algod.status().do())['last-round'] as number
#     const {
#       subscriber,
#       subscribedTestAccountTxns: subscribedTxns,
#       getWatermark,
#     } = getSubscriber(
#       {
#         testAccount,
#         // Polling for 10s means we are definitely testing the algod waiting works
#         configOverrides: { frequencyInSeconds: 10, waitForBlockWhenAtTip: true, syncBehaviour: 'sync-oldest' },
#         initialWatermark: currentRound - 1,
#       },
#       algod,
#     )
#     const roundsSynced: number[] = []

#     console.log('Starting subscriber')
#     subscriber.start((r) => roundsSynced.push(r.currentRound))

#     console.log('Waiting for up to 2s until subscriber has caught up to tip of chain')
#     await waitFor(() => roundsSynced.length > 0, 2000)

#     console.log('Issuing transaction')
#     const pollCountBeforeIssuing = roundsSynced.length
#     const { lastTxnRound, txIds } = await SendXTransactions(1, testAccount, algod)

#     console.log(`Waiting for up to 2s for round ${lastTxnRound} to get processed`)
#     await waitFor(() => subscribedTxns.length === 1, 5000)
#     const pollCountAfterIssuing = roundsSynced.length

#     console.log('Stopping subscriber')
#     await subscriber.stop('TEST')

#     // Assert
#     expect(subscribedTxns.length).toBe(1)
#     expect(subscribedTxns[0]).toBe(txIds[0])
#     expect(getWatermark()).toBeGreaterThanOrEqual(lastTxnRound)
#     // Expect at least 1 poll to have occurred
#     expect(pollCountAfterIssuing - pollCountBeforeIssuing).toBeGreaterThanOrEqual(1)
#   })
def test_waits_until_transaction_appears_by_default_when_started() -> None:
    algorand = AlgorandClient.default_local_net()
    test_account = generate_account(algorand)
    current_round = algorand.client.algod.status().get('last-round')
    subscriber = get_subscriber(
        algorand,
        test_account,
        config_overrides={
            'frequency_in_seconds': 10,
            'wait_for_block_when_at_tip': True,
            'sync_behaviour': 'sync-oldest',
        },
        initial_watermark=current_round - 1
    )
    rounds_synced = []

    start_time = time.time()
    poll_count_before_issuing = None
    poll_count_after_issuing = None
    last_txn_round = None
    tx_ids = None

    # Note: Because the python implementation is fully sync, we need to test this a bit differently
    def inspect(r: dict) -> None:
        rounds_synced.append(r['current_round'])
        nonlocal start_time

        if r['current_round'] == current_round:
            print('Issuing transaction')
            nonlocal poll_count_before_issuing
            poll_count_before_issuing = len(rounds_synced)
            results = send_x_transactions(1, test_account, algorand)

            nonlocal last_txn_round
            nonlocal tx_ids
            last_txn_round = results['last_txn_round']
            tx_ids = results['tx_ids']

        if last_txn_round and r['current_round'] >= last_txn_round:
            nonlocal poll_count_after_issuing
            poll_count_after_issuing = len(rounds_synced)

            print('Stopping subscriber')
            subscriber['subscriber'].stop('TEST')

    # Note: We might want to think of a better way to handle this within the library, but timing out for a block like this is very unlikely under normal network conditions
    with contextlib.suppress(TimeoutError):
        print('Starting subscriber')
        subscriber['subscriber'].start(inspect)


    # Assert
    assert len(subscriber['subscribed_test_account_txns']) == 1
    assert subscriber['get_watermark']() >= last_txn_round
    # Expect at least 1 poll to have occurred
    assert poll_count_after_issuing - poll_count_before_issuing >= 1

# test('Correctly fires various on* methods', async () => {
#     const { algod, testAccount, generateAccount } = localnet.context
#     const randomAccount = await generateAccount({ initialFunds: (3).algos() })
#     const { txns, txIds } = await SendXTransactions(2, testAccount, algod)
#     const { txIds: txIds2 } = await SendXTransactions(2, randomAccount, algod)
#     const initialWatermark = Number(txns[0].confirmation!.confirmedRound!) - 1
#     const eventsEmitted: string[] = []
#     let pollComplete = false
#     const { subscriber } = getSubscriber(
#       {
#         testAccount: algokit.randomAccount(),
#         initialWatermark,
#         configOverrides: {
#           maxRoundsToSync: 100,
#           syncBehaviour: 'sync-oldest',
#           frequencyInSeconds: 1000,
#           filters: [
#             {
#               name: 'account1',
#               filter: {
#                 sender: algokit.getSenderAddress(testAccount),
#               },
#             },
#             {
#               name: 'account2',
#               filter: {
#                 sender: algokit.getSenderAddress(randomAccount),
#               },
#             },
#           ],
#         },
#       },
#       algod,
#     )
#     subscriber
#       .onBatch('account1', (b) => {
#         eventsEmitted.push(`batch:account1:${b.map((b) => b.id).join(':')}`)
#       })
#       .on('account1', (t) => {
#         eventsEmitted.push(`account1:${t.id}`)
#       })
#       .onBatch('account2', (b) => {
#         eventsEmitted.push(`batch:account2:${b.map((b) => b.id).join(':')}`)
#       })
#       .on('account2', (t) => {
#         eventsEmitted.push(`account2:${t.id}`)
#       })
#       .onBeforePoll((metadata) => {
#         eventsEmitted.push(`before:poll:${metadata.watermark}`)
#       })
#       .onPoll((result) => {
#         eventsEmitted.push(`poll:${result.subscribedTransactions.map((b) => b.id).join(':')}`)
#       })

#     subscriber.start((result) => {
#       eventsEmitted.push(`inspect:${result.subscribedTransactions.map((b) => b.id).join(':')}`)
#       pollComplete = true
#     })
def test_correctly_fires_various_on_methods() -> None:
    algorand = AlgorandClient.default_local_net()
    test_account = generate_account(algorand)
    random_account = generate_account(algorand, 3 * 10**6)
    results = send_x_transactions(2, test_account, algorand)
    txns = results['txns']
    tx_ids = results['tx_ids']
    results_2 = send_x_transactions(2, random_account, algorand)
    tx_ids_2 = results_2['tx_ids']
    initial_watermark = int(txns[0]['confirmation']['confirmed-round']) - 1
    events_emitted = []

    subscriber = get_subscriber(
        algorand,
        test_account,
        config_overrides={
            'max_rounds_to_sync': 100,
            'sync_behaviour': 'sync-oldest',
            'frequency_in_seconds': 1000,
            'filters': [
                {
                    'name': 'account1',
                    'filter': {
                        'sender': test_account,
                    },
                },
                {
                    'name': 'account2',
                    'filter': {
                        'sender': random_account,
                    },
                },
            ],
        },
        initial_watermark=initial_watermark
    )

    def on_batch_account_1(b: list, e: str) -> None:
        events_emitted.append(f'batch:account1:{":".join([b['id'] for b in b])}')

    def on_account_1(t: dict, e: str) -> None:
        events_emitted.append(f'account1:{t["id"]}')

    def on_batch_account_2(b: list, e: str) -> None:
        events_emitted.append(f'batch:account2:{":".join([b['id'] for b in b])}')

    def on_account_2(t: dict, e: str) -> None:
        events_emitted.append(f'account2:{t["id"]}')

    def on_before_poll(metadata: dict, e: str) -> None:
        events_emitted.append(f'before:poll:{metadata["watermark"]}')

    def on_poll(result: dict, e: str) -> None:
        events_emitted.append(f'poll:{":".join([b['id'] for b in result["subscribed_transactions"]])}')

    def inspect(result: dict) -> None:
        events_emitted.append(f'inspect:{":".join([b['id'] for b in result["subscribed_transactions"]])}')
        subscriber['subscriber'].stop('TEST')

    subscriber['subscriber'].on_batch('account1', on_batch_account_1)
    subscriber['subscriber'].on('account1', on_account_1)
    subscriber['subscriber'].on_batch('account2', on_batch_account_2)
    subscriber['subscriber'].on('account2', on_account_2)
    subscriber['subscriber'].on_before_poll(on_before_poll)
    subscriber['subscriber'].on_poll(on_poll)

    subscriber['subscriber'].start(inspect)

    expected_batch_result = f'{tx_ids[0]}:{tx_ids[1]}:{tx_ids_2[0]}:{tx_ids_2[1]}'

    # TODO: Event order is non-deterministic, so we need to fix it
    assert events_emitted[0] == f'before:poll:{initial_watermark}'
    assert events_emitted[1] == f'batch:account1:{tx_ids[0]}:{tx_ids[1]}'
    assert events_emitted[2] == f'account1:{tx_ids[0]}'
    assert events_emitted[3] == f'account1:{tx_ids[1]}'
    assert events_emitted[4] == f'batch:account2:{tx_ids_2[0]}:{tx_ids_2[1]}'
    assert events_emitted[5] == f'account2:{tx_ids_2[0]}'
    assert events_emitted[6] == f'account2:{tx_ids_2[1]}'
    assert events_emitted[7] == f'poll:{expected_batch_result}'
    assert events_emitted[8] == f'inspect:{expected_batch_result}'

# TODO: onError test
