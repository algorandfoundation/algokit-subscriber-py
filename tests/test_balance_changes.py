
from algokit_subscriber_py.types.subscription import BalanceChangeRole
from algokit_utils.beta.algorand_client import AlgorandClient
from algokit_utils.beta.composer import AssetCreateParams, AssetDestroyParams, AssetOptInParams, AssetTransferParams, PayParams

from .accounts import generate_account
from .filter_fixture import filter_fixture  # noqa: F401
from .transactions import get_confirmations

#   test('Works for asset create transactions', async () => {
#     // Assets are always minted into the creator/sender account, even if a reserve address is supplied
#     const { testAccount, algod } = localnet.context
#     const params = await algokit.getTransactionParams(undefined, algod)
#     const txns = await algokit.sendGroupOfTransactions(
#       {
#         transactions: [
#           {
#             signer: testAccount,
#             transaction: acfgCreate(params, testAccount.addr, 2000, 100_000_000),
#           },
#         ],
#       },
#       algod,
#     )
#     const asset = txns.confirmations![0].assetIndex!

#     const subscription = await subscribeAndVerify(
#       {
#         balanceChanges: [
#           {
#             role: [BalanceChangeRole.AssetCreator],
#           },
#         ],
#       },
#       extractFromGroupResult(txns, 0),
#     )

#     const transaction = subscription.subscribedTransactions[0]
#     invariant(transaction.balanceChanges)
#     expect(transaction.balanceChanges.length).toBe(2)

#     expect(transaction.balanceChanges[0].address).toBe(testAccount.addr)
#     expect(transaction.balanceChanges[0].amount).toBe(-2000n) // min txn fee
#     expect(transaction.balanceChanges[0].roles).toEqual([BalanceChangeRole.Sender])
#     expect(transaction.balanceChanges[0].assetId).toBe(0)

#     expect(transaction.balanceChanges[1].address).toBe(testAccount.addr)
#     expect(transaction.balanceChanges[1].amount).toBe(100_000_000n)
#     expect(transaction.balanceChanges[1].roles).toEqual([BalanceChangeRole.AssetCreator])
#     expect(transaction.balanceChanges[1].assetId).toBe(asset)
#   })
def test_asset_create_txns(filter_fixture: dict) -> None:  # noqa: F811
    localnet: AlgorandClient = filter_fixture['localnet']

    sender = generate_account(localnet)
    txns = localnet.new_group().add_asset_create(AssetCreateParams(sender=sender, static_fee=2000, total=100_000_000)).execute()
    confirmations = get_confirmations(localnet, txns.tx_ids)
    asset = confirmations[0]['asset-index']

    subscription = filter_fixture['subscribe_and_verify'](
        {
            'balance_changes': [{
                'role': [BalanceChangeRole.AssetCreator]
            }],
        },
        txns.tx_ids[0]
    )

    transaction = subscription['subscribed_transactions'][0]
    assert transaction['balance_changes']
    assert len(transaction['balance_changes']) == 2

    assert transaction['balance_changes'][0]['address'] == sender
    assert transaction['balance_changes'][0]['amount'] == -2000
    assert transaction['balance_changes'][0]['roles'] == [BalanceChangeRole.Sender]
    assert transaction['balance_changes'][0]['asset_id'] == 0

    assert transaction['balance_changes'][1]['address'] == sender
    assert transaction['balance_changes'][1]['amount'] == 100_000_000
    assert transaction['balance_changes'][1]['roles'] == [BalanceChangeRole.AssetCreator]
    assert transaction['balance_changes'][1]['asset_id'] == asset

# test('Works for asset destroy transactions', async () => {
#     const { testAccount, algod } = localnet.context
#     const params = await algokit.getTransactionParams(undefined, algod)
#     const createAssetTxns = await algokit.sendGroupOfTransactions(
#       {
#         transactions: [
#           {
#             signer: testAccount,
#             transaction: acfgCreate(params, testAccount.addr, 2000, 100_000_000),
#           },
#         ],
#       },
#       algod,
#     )
#     const asset = createAssetTxns.confirmations![0].assetIndex!

#     const txns = await algokit.sendGroupOfTransactions(
#       {
#         transactions: [
#           {
#             signer: testAccount,
#             transaction: acfgDestroy(params, testAccount.addr, 2000, Number(asset)),
#           },
#         ],
#       },
#       algod,
#     )

#     const subscription = await subscribeAndVerify(
#       {
#         balanceChanges: [
#           {
#             role: [BalanceChangeRole.AssetDestroyer],
#           },
#         ],
#       },
#       extractFromGroupResult(txns, 0),
#     )

#     const transaction = subscription.subscribedTransactions[0]
#     invariant(transaction.balanceChanges)
#     expect(transaction.balanceChanges.length).toBe(2)

#     expect(transaction.balanceChanges[0].address).toBe(testAccount.addr)
#     expect(transaction.balanceChanges[0].amount).toBe(-2000n) // min txn fee
#     expect(transaction.balanceChanges[0].roles).toEqual([BalanceChangeRole.Sender])
#     expect(transaction.balanceChanges[0].assetId).toBe(0)

#     expect(transaction.balanceChanges[1].address).toBe(testAccount.addr)
#     expect(transaction.balanceChanges[1].amount).toBe(0n)
#     expect(transaction.balanceChanges[1].roles).toEqual([BalanceChangeRole.AssetDestroyer])
#     expect(transaction.balanceChanges[1].assetId).toBe(asset)
#   })
def test_asset_destroy_txns(filter_fixture: dict) -> None:  # noqa: F811
    localnet: AlgorandClient = filter_fixture['localnet']

    sender = generate_account(localnet)
    create_asset_txns = localnet.new_group().add_asset_create(AssetCreateParams(sender=sender, static_fee=2000, total=100_000_000, manager=sender)).execute()
    asset = get_confirmations(localnet, create_asset_txns.tx_ids)[0]['asset-index']

    txns = localnet.new_group().add_asset_destroy(AssetDestroyParams(sender=sender, static_fee=2000, asset_id=asset)).execute()

    subscription = filter_fixture['subscribe_and_verify'](
        {
            'balance_changes': [{
                'role': [BalanceChangeRole.AssetDestroyer]
            }],
        },
        txns.tx_ids[0]
    )

    transaction = subscription['subscribed_transactions'][0]
    assert transaction['balance_changes']
    assert len(transaction['balance_changes']) == 2

    assert transaction['balance_changes'][0]['address'] == sender
    assert transaction['balance_changes'][0]['amount'] == -2000
    assert transaction['balance_changes'][0]['roles'] == [BalanceChangeRole.Sender]
    assert transaction['balance_changes'][0]['asset_id'] == 0

    assert transaction['balance_changes'][1]['address'] == sender
    assert transaction['balance_changes'][1]['amount'] == 0
    assert transaction['balance_changes'][1]['roles'] == [BalanceChangeRole.AssetDestroyer]
    assert transaction['balance_changes'][1]['asset_id'] == asset

#  test('Works with balance change filter on fee algos', async () => {
#     const { testAccount, algod, generateAccount } = localnet.context
#     const randomAccount = await generateAccount({ initialFunds: (1).algos() })
#     const params = await algokit.getTransactionParams(undefined, algod)
#     const txns = await algokit.sendGroupOfTransactions(
#       {
#         transactions: [
#           {
#             signer: randomAccount,
#             transaction: acfgCreate(params, randomAccount.addr, 3000),
#           },
#           {
#             signer: testAccount,
#             transaction: acfgCreate(params, testAccount.addr, 1000),
#           },
#           {
#             signer: testAccount,
#             transaction: acfgCreate(params, testAccount.addr, 3000),
#           },
#           {
#             signer: testAccount,
#             transaction: acfgCreate(params, testAccount.addr, 5000),
#           },
#         ],
#       },
#       algod,
#     )

#     await subscribeAndVerifyFilter(
#       {
#         balanceChanges: [
#           {
#             assetId: [0],
#             address: testAccount.addr,
#             role: [BalanceChangeRole.Sender],
#             minAmount: -4000,
#             maxAmount: -2000,
#             minAbsoluteAmount: 2000,
#             maxAbsoluteAmount: 4000,
#           },
#         ],
#       },
#       extractFromGroupResult(txns, 2),
#     )
#   })
def test_balance_change_filter_on_fee(filter_fixture: dict) -> None:  # noqa: F811
    localnet: AlgorandClient = filter_fixture['localnet']

    random_account = generate_account(localnet, amount=1_000_000)
    test_account = generate_account(localnet)

    txns = localnet.new_group().add_asset_create(
        AssetCreateParams(sender=random_account, static_fee=3000, total=1)
    ).add_asset_create(
        AssetCreateParams(sender=test_account, static_fee=1000, total=1)
    ).add_asset_create(
        AssetCreateParams(sender=test_account, static_fee=3000, total=1)
    ).add_asset_create(
        AssetCreateParams(sender=test_account, static_fee=5000, total=1)
    ).execute()

    filter_fixture['subscribe_and_verify_filter'](
        {
            'balance_changes': [{
                'asset_id': [0],
                'address': test_account,
                'role': [BalanceChangeRole.Sender],
                'min_amount': -4000,
                'max_amount': -2000,
                'min_absolute_amount': 2000,
                'max_absolute_amount': 4000,
            }],
        },
        [txns.tx_ids[2]]
    )

#   test('Works with various balance change filters on algo transfer', async () => {
#     try {
#       const { algod, generateAccount } = localnet.context
#       const account = await generateAccount({ initialFunds: (200_000).microAlgos() })
#       const account2 = await generateAccount({ initialFunds: (200_000).microAlgos() })
#       const account3 = await generateAccount({ initialFunds: (200_000).microAlgos() })
#       const address = {
#         [account.addr]: 'account1',
#         [account2.addr]: 'account2',
#         [account3.addr]: 'account3',
#       }
#       const params = await algokit.getTransactionParams(undefined, algod)
#       const txns = await algokit.sendGroupOfTransactions(
#         {
#           transactions: [
#             pay(params, 1000, account.addr, account2.addr, 1000), // 0: account -2000, account2 +1000
#             pay(params, 1000, account2.addr, account.addr, 1000), // 1: account +1000, account2 -2000
#             pay(params, 2000, account.addr, account2.addr, 1000), // 2: account -3000, account2 +2000
#             pay(params, 2000, account2.addr, account.addr, 1000), // 3: account +2000, account2 -3000
#             pay(params, 3000, account.addr, account2.addr, 1000), // 4: account -4000, account2 +3000
#             pay(params, 3000, account2.addr, account.addr, 1000), // 5: account +3000, account2 -4000
#             // account 197k, account2 197k, account3 200k
#             pay(params, 100_000, account.addr, account2.addr, 1000, account3.addr), // 6: account -197k, account2 +100k, account3 +96k
#             pay(params, 100_000, account2.addr, account.addr, 1000, account.addr), // 7: account +296k, account2 -297k
#             pay(params, 100_000, account3.addr, account2.addr, 2000, account.addr), // 8: account +194k, account2 +100k, account3 -296k
#             pay(params, 0, account.addr, account.addr, 0), // 9: account 0 (fee covered by previous)
#           ].map((transaction) => ({
#             signer:
#               algosdk.encodeAddress(transaction.from.publicKey) === account.addr
#                 ? account
#                 : algosdk.encodeAddress(transaction.from.publicKey) === account2.addr
#                   ? account2
#                   : account3,
#             transaction,
#           })),
#         },
#         algod,
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               assetId: [0],
#               address: account.addr,
#               role: [BalanceChangeRole.Sender],
#               minAbsoluteAmount: 2001,
#               maxAbsoluteAmount: 3000,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 2),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               assetId: [0],
#               address: account.addr,
#               role: [BalanceChangeRole.Sender],
#               minAmount: -3000,
#               maxAmount: -2001,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 2),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               assetId: [0],
#               address: account.addr,
#               minAmount: -2000,
#               maxAmount: -2000,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 0),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               assetId: [0],
#               address: account.addr,
#               minAmount: 1000,
#               maxAmount: 1000,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 1),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               assetId: [0],
#               address: account2.addr,
#               role: [BalanceChangeRole.Sender],
#               minAmount: -3000,
#               maxAmount: -2001,
#               minAbsoluteAmount: 2001,
#               maxAbsoluteAmount: 3000,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 3),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               assetId: [0],
#               address: account.addr,
#               minAbsoluteAmount: 1,
#               maxAbsoluteAmount: 1000,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 1),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               assetId: [0],
#               address: account2.addr,
#               maxAbsoluteAmount: 1000,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 0),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               assetId: [0],
#               address: account3.addr,
#               role: BalanceChangeRole.CloseTo,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 6),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               assetId: [0],
#               address: account3.addr,
#               role: [BalanceChangeRole.CloseTo, BalanceChangeRole.Sender],
#               minAmount: 0,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 6),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               minAmount: 196_000,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 7),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               address: [account2.addr, account3.addr],
#               minAbsoluteAmount: 296_000,
#               maxAbsoluteAmount: 296_000,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 8),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               minAbsoluteAmount: 297_000,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 7),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               maxAmount: -297_000,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 7),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           balanceChanges: [
#             {
#               minAmount: 0,
#               maxAmount: 0,
#             },
#           ],
#         },
#         extractFromGroupResult(txns, 9),
#       )

#       const result = await subscribeAlgod({ balanceChanges: [{ minAmount: 0 }] }, extractFromGroupResult(txns, 0))
#       const balanceChanges = result.subscribedTransactions.map((s) =>
#         s
#           .balanceChanges!.map((b) => ({
#             ...b,
#             address: address[b.address],
#           }))
#           .sort((a, b) => a.address.localeCompare(b.address))
#           .map((b) => `${b.address}: ${Number(b.amount)} (${b.roles.join(', ')})`),
#       )
#       expect(balanceChanges).toMatchInlineSnapshot(`
#         [
#           [
#             "account1: -2000 (Sender)",
#             "account2: 1000 (Receiver)",
#           ],
#           [
#             "account1: 1000 (Receiver)",
#             "account2: -2000 (Sender)",
#           ],
#           [
#             "account1: -3000 (Sender)",
#             "account2: 2000 (Receiver)",
#           ],
#           [
#             "account1: 2000 (Receiver)",
#             "account2: -3000 (Sender)",
#           ],
#           [
#             "account1: -4000 (Sender)",
#             "account2: 3000 (Receiver)",
#           ],
#           [
#             "account1: 3000 (Receiver)",
#             "account2: -4000 (Sender)",
#           ],
#           [
#             "account1: -197000 (Sender)",
#             "account2: 100000 (Receiver)",
#             "account3: 96000 (CloseTo)",
#           ],
#           [
#             "account1: 296000 (Receiver, CloseTo)",
#             "account2: -297000 (Sender)",
#           ],
#           [
#             "account1: 194000 (CloseTo)",
#             "account2: 100000 (Receiver)",
#             "account3: -296000 (Sender)",
#           ],
#           [
#             "account1: 0 (Sender, Receiver)",
#           ],
#         ]
#       `)
#     } catch (e) {
#       // eslint-disable-next-line no-console
#       console.error(e)
#       throw e
#     }
#   }, 30_000)
def test_various_filters_on_payments(filter_fixture: dict) -> None:  # noqa: F811
    localnet: AlgorandClient = filter_fixture['localnet']
    subscribe_and_verify_filter = filter_fixture['subscribe_and_verify_filter']

    account = generate_account(localnet, 200_000)
    account2 = generate_account(localnet, 200_000)
    account3 = generate_account(localnet, 200_000)


        # pay(params, 1000, account.addr, account2.addr, 1000), // 0: account -2000, account2 +1000
        # pay(params, 1000, account2.addr, account.addr, 1000), // 1: account +1000, account2 -2000
        # pay(params, 2000, account.addr, account2.addr, 1000), // 2: account -3000, account2 +2000
        # pay(params, 2000, account2.addr, account.addr, 1000), // 3: account +2000, account2 -3000
        # pay(params, 3000, account.addr, account2.addr, 1000), // 4: account -4000, account2 +3000
        # pay(params, 3000, account2.addr, account.addr, 1000), // 5: account +3000, account2 -4000
        # // account 197k, account2 197k, account3 200k
        # pay(params, 100_000, account.addr, account2.addr, 1000, account3.addr), // 6: account -197k, account2 +100k, account3 +96k
        # pay(params, 100_000, account2.addr, account.addr, 1000, account.addr), // 7: account +296k, account2 -297k
        # pay(params, 100_000, account3.addr, account2.addr, 2000, account.addr), // 8: account +194k, account2 +100k, account3 -296k
        # pay(params, 0, account.addr, account.addr, 0), // 9: account 0 (fee covered by previous)
    txns = localnet.new_group().add_payment(
        PayParams(
            amount=1000,
            sender=account,
            receiver=account2,
            static_fee=1000
        )
    ).add_payment(
        PayParams(
            amount=1000,
            sender=account2,
            receiver=account,
            static_fee=1000
        )
    ).add_payment(
        PayParams(
            amount=2000,
            sender=account,
            receiver=account2,
            static_fee=1000
        )
    ).add_payment(
        PayParams(
            amount=2000,
            sender=account2,
            receiver=account,
            static_fee=1000
        )
    ).add_payment(
        PayParams(
            amount=3000,
            sender=account,
            receiver=account2,
            static_fee=1000
        )
    ).add_payment(
        PayParams(
            amount=3000,
            sender=account2,
            receiver=account,
            static_fee=1000
        )
    ).add_payment(
        PayParams(
            amount=100_000,
            sender=account,
            receiver=account2,
            static_fee=1000,
            close_remainder_to=account3
        )
    ).add_payment(
        PayParams(
            amount=100_000,
            sender=account2,
            receiver=account,
            static_fee=1000,
            close_remainder_to=account
        )
    ).add_payment(
        PayParams(
            amount=100_000,
            sender=account3,
            receiver=account2,
            static_fee=2000,
            close_remainder_to=account
        )
    ).add_payment(
        PayParams(
            amount=0,
            sender=account,
            receiver=account,
            static_fee=0
        )
    ).execute()

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [0],
                'address': account,
                'role': [BalanceChangeRole.Sender],
                'min_absolute_amount': 2001,
                'max_absolute_amount': 3000,
            }],
        },
        txns.tx_ids[2]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [0],
                'address': account,
                'role': [BalanceChangeRole.Sender],
                'min_amount': -3000,
                'max_amount': -2001,
            }],
        },
        txns.tx_ids[2]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [0],
                'address': account,
                'min_amount': -2000,
                'max_amount': -2000,
            }],
        },
        txns.tx_ids[0]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [0],
                'address': account,
                'min_amount': 1000,
                'max_amount': 1000,
            }],
        },
        txns.tx_ids[1]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [0],
                'address': account2,
                'role': [BalanceChangeRole.Sender],
                'min_amount': -3000,
                'max_amount': -2001,
                'min_absolute_amount': 2001,
                'max_absolute_amount': 3000,
            }],
        },
        txns.tx_ids[3]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [0],
                'address': account,
                'min_absolute_amount': 1,
                'max_absolute_amount': 1000,
            }],
        },
        txns.tx_ids[1]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [0],
                'address': account2,
                'max_absolute_amount': 1000,
            }],
        },
        txns.tx_ids[0]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [0],
                'address': account3,
                'role': BalanceChangeRole.CloseTo,
            }],
        },
        txns.tx_ids[6]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [0],
                'address': account3,
                'role': [BalanceChangeRole.CloseTo, BalanceChangeRole.Sender],
                'min_amount': 0,
            }],
        },
        txns.tx_ids[6]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'min_amount': 196_000,
            }],
        },
        txns.tx_ids[7]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'address': [account2, account3],
                'min_absolute_amount': 296_000,
                'max_absolute_amount': 296_000,
            }],
        },
        txns.tx_ids[8]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'min_absolute_amount': 297_000,
            }],
        },
        txns.tx_ids[7]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'max_amount': -297_000,
            }],
        },
        txns.tx_ids[7]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'min_amount': 0,
                'max_amount': 0,
            }],
        },
        txns.tx_ids[9]
    )

    # TODO: Check balance change output (like the snapshot in the TS test)
    # address = {}

    # address[account] = 'account1'
    # address[account2] = 'account2'
    # address[account3] = 'account3'
    # result = filter_fixture['subscribe_algod'](
    #     { 'balance_changes': [{ 'min_amount': 0 }] },
    #     localnet.client.algod.pending_transaction_info(txns.tx_ids[0])["confirmed-round"]
    # )


# test('Works with various balance change filters on asset transfer', async () => {
#     try {
#       const { algod, generateAccount, testAccount } = localnet.context
#       const account = await generateAccount({ initialFunds: (1).algos() })
#       const account2 = await generateAccount({ initialFunds: (1).algos() })
#       const account3 = await generateAccount({ initialFunds: (1).algos() })
#       const params = await algokit.getTransactionParams(undefined, algod)
#       const asset1 = Number(
#         (
#           await algokit.sendTransaction(
#             {
#               transaction: acfgCreate(params, testAccount.addr, 1000),
#               from: testAccount,
#             },
#             algod,
#           )
#         ).confirmation!.assetIndex!,
#       )
#       const asset2 = Number(
#         (
#           await algokit.sendTransaction(
#             {
#               transaction: acfgCreate(params, testAccount.addr, 1001),
#               from: testAccount,
#             },
#             algod,
#           )
#         ).confirmation!.assetIndex!,
#       )
#       // eslint-disable-next-line no-console
#       console.log('accounts', [testAccount.addr, account.addr, account2.addr, account3.addr], 'assets', [asset1, asset2])
#       const address = {
#         [testAccount.addr]: 'testAccount',
#         [account.addr]: 'account1',
#         [account2.addr]: 'account2',
#         [account3.addr]: 'account3',
#       }
#       const asset = {
#         [asset1]: 'asset1',
#         [asset2]: 'asset2',
#       }
#       await algokit.assetOptIn({ account: account, assetId: asset1 }, algod)
#       await algokit.assetOptIn({ account: account2, assetId: asset1 }, algod)
#       await algokit.assetOptIn({ account: account3, assetId: asset1 }, algod)
#       await algokit.assetOptIn({ account: account, assetId: asset2 }, algod)
#       await algokit.assetOptIn({ account: account2, assetId: asset2 }, algod)
#       await algokit.assetOptIn({ account: account3, assetId: asset2 }, algod)
#       await algokit.transferAsset({ amount: 10, from: testAccount, to: account, assetId: asset1 }, algod)
#       await algokit.transferAsset({ amount: 10, from: testAccount, to: account2, assetId: asset1 }, algod)
#       await algokit.transferAsset({ amount: 20, from: testAccount, to: account3, assetId: asset1 }, algod)
#       await algokit.transferAsset({ amount: 10, from: testAccount, to: account, assetId: asset2 }, algod)
#       await algokit.transferAsset({ amount: 23, from: testAccount, to: account2, assetId: asset2 }, algod)
#       // a1: account 10, account2 10, account3 0
#       // a2: account 10, account2 10, account3 0
#       const txns = await algokit.sendGroupOfTransactions(
#         {
#           transactions: [
#             axfer(params, asset1, 1, account.addr, account2.addr), // 0: a1: account -1, account2 +1
#             axfer(params, asset1, 1, account2.addr, account.addr), // 1: a1: account +1, account2 -1
#             axfer(params, asset1, 2, account.addr, account2.addr), // 2: a1: account -2, account2 +2
#             axfer(params, asset1, 2, account2.addr, account.addr), // 3: a1: account +2, account2 -2
#             axfer(params, asset1, 3, testAccount.addr, account2.addr, account.addr), // 4: a1: account -3, account2 +3 (clawback)
#             axfer(params, asset1, 3, testAccount.addr, account.addr, account2.addr), // 5: a1: account +3, account2 -3 (clawback)
#             axfer(params, asset1, 7, account.addr, account2.addr, undefined, account3.addr), // 6: a1: account -10, account2 +7, account3 +3
#             (await algokit.assetOptIn({ account: account, assetId: asset1, skipSending: true }, algod)).transaction, // 7: Opt-in account to asset1 again
#             axfer(params, asset1, 7, account2.addr, account.addr, undefined, account.addr), // 8: a1: account +17, account2 -17
#             (await algokit.assetOptIn({ account: account2, assetId: asset1, skipSending: true }, algod)).transaction, // 9: Opt-in account2 to asset1 again
#             axfer(params, asset1, 3, account3.addr, account2.addr, undefined, account.addr), // 10: a1: account +20, account2 +3, account3 -23
#             axfer(params, asset2, 1, account.addr, account2.addr), // 11: a2: account -1, account2 +1
#             axfer(params, asset2, 23, account2.addr, account.addr), // 12: a2: account +23, account2 -23
#           ].map((transaction) => ({
#             signer:
#               algosdk.encodeAddress(transaction.from.publicKey) === account.addr
#                 ? account
#                 : algosdk.encodeAddress(transaction.from.publicKey) === account2.addr
#                   ? account2
#                   : algosdk.encodeAddress(transaction.from.publicKey) === testAccount.addr
#                     ? testAccount
#                     : account3,
#             transaction,
#           })),
#         },
#         algod,
#       )
def test_various_filters_on_axfers(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture['localnet']
    subscribe_and_verify_filter = filter_fixture['subscribe_and_verify_filter']

    test_account = generate_account(localnet)
    account = generate_account(localnet, 1_000_000)
    account2 = generate_account(localnet, 1_000_000)
    account3 = generate_account(localnet, 1_000_000)

    asset1 = localnet.send.asset_create(AssetCreateParams(sender=test_account, total=1000, clawback=test_account))['confirmation']['asset-index']
    asset2 = localnet.send.asset_create(AssetCreateParams(sender=test_account, total=1001, clawback=test_account))['confirmation']['asset-index']

    localnet.send.asset_opt_in(AssetOptInParams(sender=account, asset_id=asset1))
    localnet.send.asset_opt_in(AssetOptInParams(sender=account2, asset_id=asset1))
    localnet.send.asset_opt_in(AssetOptInParams(sender=account3, asset_id=asset1))
    localnet.send.asset_opt_in(AssetOptInParams(sender=account, asset_id=asset2))
    localnet.send.asset_opt_in(AssetOptInParams(sender=account2, asset_id=asset2))
    localnet.send.asset_opt_in(AssetOptInParams(sender=account3, asset_id=asset2))

    localnet.send.asset_transfer(AssetTransferParams(sender=test_account, receiver=account, asset_id=asset1, amount=10))
    localnet.send.asset_transfer(AssetTransferParams(sender=test_account, receiver=account2, asset_id=asset1, amount=10))
    localnet.send.asset_transfer(AssetTransferParams(sender=test_account, receiver=account3, asset_id=asset1, amount=20))
    localnet.send.asset_transfer(AssetTransferParams(sender=test_account, receiver=account, asset_id=asset2, amount=10))
    localnet.send.asset_transfer(AssetTransferParams(sender=test_account, receiver=account2, asset_id=asset2, amount=23))

    txns = localnet.new_group().add_asset_transfer(
        AssetTransferParams(sender=account, receiver=account2, asset_id=asset1, amount=1)
    ).add_asset_transfer(
        AssetTransferParams(sender=account2, receiver=account, asset_id=asset1, amount=1)
    ).add_asset_transfer(
        AssetTransferParams(sender=account, receiver=account2, asset_id=asset1, amount=2)
    ).add_asset_transfer(
        AssetTransferParams(sender=account2, receiver=account, asset_id=asset1, amount=2)
    ).add_asset_transfer(
        AssetTransferParams(sender=test_account, receiver=account2, asset_id=asset1, amount=3, clawback_target=account)
    ).add_asset_transfer(
        AssetTransferParams(sender=test_account, receiver=account, asset_id=asset1, amount=3, clawback_target=account2)
    ).add_asset_transfer(
        AssetTransferParams(sender=account, receiver=account2, asset_id=asset1, amount=7, close_asset_to=account3)
    ).add_asset_opt_in(
        AssetOptInParams(sender=account, asset_id=asset1)
    ).add_asset_transfer(
        AssetTransferParams(sender=account2, receiver=account, asset_id=asset1, amount=7, close_asset_to=account)
    ).add_asset_opt_in(
        AssetOptInParams(sender=account2, asset_id=asset1)
    ).add_asset_transfer(
        AssetTransferParams(sender=account3, receiver=account2, asset_id=asset1, amount=3, close_asset_to=account)
    ).add_asset_transfer(
        AssetTransferParams(sender=account, receiver=account2, asset_id=asset2, amount=1)
    ).add_asset_transfer(
        AssetTransferParams(sender=account2, receiver=account, asset_id=asset2, amount=23)
    ).execute()

    #  await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           assetId: [asset1],
    #           address: account.addr,
    #           role: [BalanceChangeRole.Sender],
    #           minAbsoluteAmount: 1.1,
    #           maxAbsoluteAmount: 2,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 2),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           assetId: [asset1],
    #           address: account.addr,
    #           role: [BalanceChangeRole.Sender],
    #           minAmount: -2,
    #           maxAmount: -1.1,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 2),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           assetId: [asset1],
    #           address: account.addr,
    #           minAmount: -1,
    #           maxAmount: -1,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 0),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           assetId: [asset1],
    #           address: account.addr,
    #           minAmount: 1,
    #           maxAmount: 1,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 1),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           assetId: [asset1],
    #           address: account2.addr,
    #           role: [BalanceChangeRole.Sender],
    #           minAmount: -2,
    #           maxAmount: -1.1,
    #           minAbsoluteAmount: 1.1,
    #           maxAbsoluteAmount: 2,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 3),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           assetId: [asset1],
    #           address: account.addr,
    #           minAmount: 0.1,
    #           maxAbsoluteAmount: 1,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 1),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           assetId: [asset1],
    #           address: account2.addr,
    #           minAmount: 0.1,
    #           maxAbsoluteAmount: 1,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 0),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           assetId: [asset1],
    #           address: account3.addr,
    #           role: BalanceChangeRole.CloseTo,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 6),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           assetId: [asset1],
    #           address: account3.addr,
    #           role: [BalanceChangeRole.CloseTo, BalanceChangeRole.Sender],
    #           minAmount: 0,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 6),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           assetId: [asset1],
    #           minAmount: 18,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 10),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           address: [account2.addr, account3.addr],
    #           minAbsoluteAmount: 17,
    #           maxAbsoluteAmount: 17,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 8),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           assetId: [asset1],
    #           minAbsoluteAmount: 23,
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 10),
    #   )

    #   await subscribeAndVerifyFilter(
    #     {
    #       balanceChanges: [
    #         {
    #           address: account2.addr,
    #           maxAmount: -23,
    #           maxAbsoluteAmount: 23, // Stop algo balance changes triggering it
    #         },
    #       ],
    #     },
    #     extractFromGroupResult(txns, 12),
    #   )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [asset1],
                'address': account,
                'role': [BalanceChangeRole.Sender],
                'min_absolute_amount': 1.1,
                'max_absolute_amount': 2,
            }],
        },
        txns.tx_ids[2]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [asset1],
                'address': account,
                'role': [BalanceChangeRole.Sender],
                'min_amount': -2,
                'max_amount': -1.1,
            }],
        },
        txns.tx_ids[2]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [asset1],
                'address': account,
                'min_amount': -1,
                'max_amount': -1,
            }],
        },
        txns.tx_ids[0]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [asset1],
                'address': account,
                'min_amount': 1,
                'max_amount': 1,
            }],
        },
        txns.tx_ids[1]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [asset1],
                'address': account2,
                'role': [BalanceChangeRole.Sender],
                'min_amount': -2,
                'max_amount': -1.1,
                'min_absolute_amount': 1.1,
                'max_absolute_amount': 2,
            }],
        },
        txns.tx_ids[3]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [asset1],
                'address': account,
                'min_amount': 0.1,
                'max_absolute_amount': 1,
            }],
        },
        txns.tx_ids[1]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [asset1],
                'address': account2,
                'min_amount': 0.1,
                'max_absolute_amount': 1,
            }],
        },
        txns.tx_ids[0]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [asset1],
                'address': account3,
                'role': BalanceChangeRole.CloseTo,
            }],
        },
        txns.tx_ids[6]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [asset1],
                'address': account3,
                'role': [BalanceChangeRole.CloseTo, BalanceChangeRole.Sender],
                'min_amount': 0,
            }],
        },
        txns.tx_ids[6]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [asset1],
                'min_amount': 18,
            }],
        },
        txns.tx_ids[10]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'address': [account2, account3],
                'min_absolute_amount': 17,
                'max_absolute_amount': 17,
            }],
        },
        txns.tx_ids[8]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'asset_id': [asset1],
                'min_absolute_amount': 23,
            }],
        },
        txns.tx_ids[10]
    )

    subscribe_and_verify_filter(
        {
            'balance_changes': [{
                'address': account2,
                'max_amount': -23,
                'max_absolute_amount': 23,  # Stop algo balance changes triggering it
            }],
        },
        txns.tx_ids[12]
    )

    # TODO: Check balance change output (like the snapshot in the TS test)
