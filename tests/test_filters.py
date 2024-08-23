

from algokit_utils.beta.algorand_client import AlgorandClient
from algokit_utils.beta.composer import AssetCreateParams, AssetOptInParams, AssetTransferParams, PayParams
from algosdk.atomic_transaction_composer import AtomicTransactionComposer

from .accounts import generate_account
from .contracts.testing_app_client import TestingAppClient
from .filter_fixture import filter_fixture  # noqa: F401


def app(localnet: AlgorandClient, creator: str, *, create: bool) -> dict:
    signer = localnet.account.get_signer(creator)
    app = TestingAppClient(
        app_id=0,
        algod_client=localnet.client.algod,
        sender=creator,
        signer=signer,
    )

    if create:
        create_result = app.create_bare()
        tx_id = create_result.tx_id
        creation = localnet.client.algod.pending_transaction_info(tx_id)
    else:
        creation = None

    return {
        "app": app,
        "transaction": app.compose().create_bare().atc.build_group()[0],
        "creation": creation,
    }

# const algoTransfersFixture = async () => {
#     const { algod, generateAccount } = localnet.context
#     const testAccount = await generateAccount({ initialFunds: (10).algos() })
#     const account2 = await generateAccount({ initialFunds: (3).algos() })
#     const account3 = algokit.randomAccount()
#     const txns = await algokit.sendGroupOfTransactions(
#       {
#         transactions: [
#           await algokit.transferAlgos({ amount: (1).algos(), from: testAccount, to: account2, note: 'a', skipSending: true }, algod),
#           await algokit.transferAlgos({ amount: (2).algos(), from: testAccount, to: account3, note: 'b', skipSending: true }, algod),
#           await algokit.transferAlgos({ amount: (1).algos(), from: account2, to: testAccount, note: 'c', skipSending: true }, algod),
#         ].map((t) => ({
#           transaction: t.transaction,
#           signer: algosdk.encodeAddress(t.transaction.from.publicKey) === testAccount.addr ? testAccount : account2,
#         })),
#       },
#       algod,
#     )

#     algoTransfersData = {
#       testAccount,
#       account2,
#       account3,
#       txns,
#     }
#   }
def algo_transfers_fixture() -> dict:
    algorand: AlgorandClient = AlgorandClient.default_local_net()

    test_account = generate_account(algorand, 10_000_000)
    account2 = generate_account(algorand, 3_000_000)
    account3 = algorand.account.random()

    txns = algorand.new_group().add_payment(
        PayParams(sender=test_account, receiver=account2, amount=1_000_000, note=b'a')
    ).add_payment(
        PayParams(sender=test_account, receiver=account3.address, amount=2_000_000, note=b'b')
    ).add_payment(
            PayParams(sender=account2, receiver=test_account, amount=1_000_000, note=b'c')
    ).execute()

    return {
        'test_account': test_account,
        'account2': account2,
        'account3': account3,
        'txns': txns,
    }

# const assetsFixture = async () => {
#     const { algod, generateAccount } = localnet.context
#     const testAccount = await generateAccount({ initialFunds: (10).algos() })
#     const asset1 = await createAsset(testAccount)
#     const asset2 = await createAsset()
#     const txns = await algokit.sendGroupOfTransactions(
#       {
#         transactions: [
#           algokit.assetOptIn({ account: testAccount, assetId: asset1.assetId, skipSending: true }, algod),
#           algokit.assetOptIn({ account: testAccount, assetId: asset2.assetId, skipSending: true }, algod),
#           await createAssetTxn(testAccount),
#           algokit.transferAsset({ assetId: asset1.assetId, amount: 1, from: testAccount, to: testAccount, skipSending: true }, algod),
#           algokit.transferAsset({ assetId: asset1.assetId, amount: 2, from: testAccount, to: testAccount, skipSending: true }, algod),
#         ],
#         signer: testAccount,
#       },
#       algod,
#     )

#     assetsData = {
#       asset1,
#       asset2,
#       testAccount,
#       txns,
#     }
def asset_transfers_fixture() -> dict:
    algorand: AlgorandClient = AlgorandClient.default_local_net()

    test_account = generate_account(algorand, 10_000_000)
    asset1 = algorand.send.asset_create(AssetCreateParams(sender=test_account, total=100))['confirmation']['asset-index']
    asset2 = algorand.send.asset_create(AssetCreateParams(sender=test_account, total=101))['confirmation']['asset-index']
    txns = algorand.new_group().add_asset_opt_in(
        AssetOptInParams(sender=test_account, asset_id=asset1)
    ).add_asset_opt_in(
        AssetOptInParams(sender=test_account, asset_id=asset2)
    ).add_asset_create(
        AssetCreateParams(sender=test_account, total=103)
    ).add_asset_transfer(
        AssetTransferParams(sender=test_account, receiver=test_account, asset_id=asset1, amount=1)
    ).add_asset_transfer(
        AssetTransferParams(sender=test_account, receiver=test_account, asset_id=asset1, amount=2)
    ).execute()
    return {
        'asset1': asset1,
        'asset2': asset2,
        'test_account': test_account,
        'txns': txns,
    }

# const appsFixture = async () => {
#     const { algod, generateAccount } = localnet.context
#     const testAccount = await generateAccount({ initialFunds: (10).algos() })
#     const app1 = await app({ create: true })
#     const app2 = await app({ create: true })
#     const txns = await algokit.sendGroupOfTransactions(
#       {
#         transactions: [
#           app1.app.callAbi({ value: 'test1' }, { sender: testAccount, sendParams: { skipSending: true } }),
#           app2.app.callAbi({ value: 'test2' }, { sender: testAccount, sendParams: { skipSending: true } }),
#           (await app({ create: false }, testAccount)).creation.transaction,
#           app1.app.optIn.optIn({}, { sender: testAccount, sendParams: { skipSending: true } }),
#         ],
#         signer: testAccount,
#       },
#       algod,
#     )

#     appData = {
#       app1,
#       app2,
#       testAccount,
#       txns,
#     }
#   }
def apps_fixture() -> dict:
    algorand: AlgorandClient = AlgorandClient.default_local_net()

    test_account = generate_account(algorand, 10_000_000)
    app1: TestingAppClient = app(algorand, test_account, create=True)['app']
    app2: TestingAppClient = app(algorand, test_account, create=True)['app']

    app1_call = app1.compose().call_abi(value='test1').atc.build_group()[0]
    app2_call = app2.compose().call_abi(value='test2').atc.build_group()[0]
    app_create = app(algorand, test_account, create=False)['transaction']
    app1_opt_in = app1.compose().opt_in_opt_in().atc.build_group()[0]

    atc = AtomicTransactionComposer()

    atc.add_transaction(app1_call)
    atc.add_transaction(app2_call)
    atc.add_transaction(app_create)
    atc.add_transaction(app1_opt_in)

    txns = algorand.new_group().add_atc(atc).execute()

    return {
        'app1': app1,
        'app2': app2,
        'test_account': test_account,
        'txns': txns,
    }


# test('Single receiver', async () => {
#       const { account2, txns } = algoTransfersData!

#       await subscribeAndVerifyFilter(
#         {
#           receiver: account2.addr,
#         },
#         extractFromGroupResult(txns, 0),
#       )
#     })
def test_single_receiver(filter_fixture: dict) -> None:
    algo_transfers_data = algo_transfers_fixture()
    account2 = algo_transfers_data['account2']
    txns = algo_transfers_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify']

    subscribe_and_verify(
        {
            'receiver': account2,
        },
        txns.tx_ids[0]
    )



#     test('Single sender', async () => {
#       const { account2, txns } = algoTransfersData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: account2.addr,
#         },
#         extractFromGroupResult(txns, 2),
#       )
#     })



#     test('Multiple receivers', async () => {
#       const { account2, account3, txns } = algoTransfersData!

#       await subscribeAndVerifyFilter(
#         {
#           receiver: [account2.addr, account3.addr],
#         },
#         [extractFromGroupResult(txns, 0), extractFromGroupResult(txns, 1)],
#       )
#     })
#     test('Multiple senders', async () => {
#       const { testAccount, account2, txns } = algoTransfersData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: [testAccount.addr, account2.addr],
#         },
#         [extractFromGroupResult(txns, 0), extractFromGroupResult(txns, 1), extractFromGroupResult(txns, 2)],
#       )
#     })

#     test('Works for min amount of algos', async () => {
#       const { testAccount, txns } = algoTransfersData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           minAmount: (1).algos().microAlgos + 1,
#         },
#         extractFromGroupResult(txns, 1),
#       )
#     })

#     test('Works for max amount of algos', async () => {
#       const { testAccount, txns } = algoTransfersData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           maxAmount: (1).algos().microAlgos + 1,
#         },
#         extractFromGroupResult(txns, 0),
#       )
#     })

#     test('Works for note prefix', async () => {
#       const { testAccount, txns } = algoTransfersData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           notePrefix: 'a',
#         },
#         extractFromGroupResult(txns, 0),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           notePrefix: 'b',
#         },
#         extractFromGroupResult(txns, 1),
#       )
#     })
#   })
def test_single_sender(filter_fixture: dict) -> None:
    algo_transfers_data = algo_transfers_fixture()
    account2 = algo_transfers_data['account2']
    txns = algo_transfers_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify']

    subscribe_and_verify(
        {
            'sender': account2,
        },
        txns.tx_ids[2]
    )

def test_multiple_receivers(filter_fixture: dict) -> None:
    algo_transfers_data = algo_transfers_fixture()
    account2 = algo_transfers_data['account2']
    account3 = algo_transfers_data['account3']
    txns = algo_transfers_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify_filter']

    subscribe_and_verify(
        {
            'receiver': [account2, account3.address],
        },
        [txns.tx_ids[0], txns.tx_ids[1]]
    )

def test_multiple_senders(filter_fixture: dict) -> None:
    algo_transfers_data = algo_transfers_fixture()
    test_account = algo_transfers_data['test_account']
    account2 = algo_transfers_data['account2']
    txns = algo_transfers_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify_filter']

    subscribe_and_verify(
        {
            'sender': [test_account, account2],
        },
        txns.tx_ids
    )

def test_min_amount_of_algos(filter_fixture: dict) -> None:
    algo_transfers_data = algo_transfers_fixture()
    test_account = algo_transfers_data['test_account']
    txns = algo_transfers_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify']

    subscribe_and_verify(
        {
            'sender': test_account,
            'min_amount': 1_000_001,  # 1 Algo + 1 microAlgo
        },
        txns.tx_ids[1]
    )

def test_max_amount_of_algos(filter_fixture: dict) -> None:
    algo_transfers_data = algo_transfers_fixture()
    test_account = algo_transfers_data['test_account']
    txns = algo_transfers_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify']

    subscribe_and_verify(
        {
            'sender': test_account,
            'max_amount': 1_000_001,  # 1 Algo + 1 microAlgo
        },
        txns.tx_ids[0]
    )

def test_note_prefix(filter_fixture: dict) -> None:
    algo_transfers_data = algo_transfers_fixture()
    test_account = algo_transfers_data['test_account']
    txns = algo_transfers_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify']

    subscribe_and_verify(
        {
            'sender': test_account,
            'note_prefix': 'a',
        },
        txns.tx_ids[0]
    )

    subscribe_and_verify(
        {
            'sender': test_account,
            'note_prefix': 'b',
        },
        txns.tx_ids[1]
    )

# describe('Asset transactions', () => {
#     test('Works for single asset ID', async () => {
#       const { testAccount, asset1, txns } = assetsData!
#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           assetId: asset1.assetId,
#         },
#         [extractFromGroupResult(txns, 0), extractFromGroupResult(txns, 3), extractFromGroupResult(txns, 4)],
#       )
#     })
def test_asset_txns(filter_fixture: dict) -> None:
    asset_transfers_data = asset_transfers_fixture()
    test_account = asset_transfers_data['test_account']
    asset1 = asset_transfers_data['asset1']
    txns = asset_transfers_data['txns']
    subscribe_and_verify_filter = filter_fixture['subscribe_and_verify_filter']

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'asset_id': asset1,
        },
        [txns.tx_ids[0], txns.tx_ids[3], txns.tx_ids[4]]
    )

#     test('Works for multiple asset IDs', async () => {
#       const { testAccount, asset1, asset2, txns } = assetsData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           assetId: [asset1.assetId, asset2.assetId],
#         },
#         [
#           extractFromGroupResult(txns, 0),
#           extractFromGroupResult(txns, 1),
#           extractFromGroupResult(txns, 3),
#           extractFromGroupResult(txns, 4),
#         ],
#       )
#     })

#     test('Works for asset create', async () => {
#       const { testAccount, txns } = assetsData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           assetCreate: true,
#         },
#         extractFromGroupResult(txns, 2),
#       )
#     })

#     test('Works for transaction type(s)', async () => {
#       const { testAccount, txns } = assetsData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           type: TransactionType.axfer,
#         },
#         [
#           extractFromGroupResult(txns, 0),
#           extractFromGroupResult(txns, 1),
#           extractFromGroupResult(txns, 3),
#           extractFromGroupResult(txns, 4),
#         ],
#       )

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           type: TransactionType.acfg,
#         },
#         extractFromGroupResult(txns, 2),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           type: [TransactionType.acfg, TransactionType.axfer],
#         },
#         [
#           extractFromGroupResult(txns, 0),
#           extractFromGroupResult(txns, 1),
#           extractFromGroupResult(txns, 2),
#           extractFromGroupResult(txns, 3),
#           extractFromGroupResult(txns, 4),
#         ],
#       )
#     })

#     test('Works for min amount of asset', async () => {
#       const { testAccount, txns } = assetsData!

#       await subscribeAndVerifyFilter(
#         {
#           type: TransactionType.axfer,
#           sender: testAccount.addr,
#           minAmount: 2,
#         },
#         extractFromGroupResult(txns, 4),
#       )
#     })

#     test('Works for max amount of asset', async () => {
#       const { testAccount, txns } = assetsData!

#       await subscribeAndVerifyFilter(
#         {
#           type: TransactionType.axfer,
#           sender: testAccount.addr,
#           maxAmount: 1,
#         },
#         [extractFromGroupResult(txns, 0), extractFromGroupResult(txns, 1), extractFromGroupResult(txns, 3)],
#       )
#     })

#     test('Works for max amount of asset with asset ID', async () => {
#       const { testAccount, txns, asset1 } = assetsData!

#       await subscribeAndVerifyFilter(
#         {
#           type: TransactionType.axfer,
#           sender: testAccount.addr,
#           maxAmount: 1,
#           assetId: asset1.assetId,
#         },
#         [extractFromGroupResult(txns, 0), extractFromGroupResult(txns, 3)],
#       )
#     })

#     test('Works for min and max amount of asset with asset ID', async () => {
#       const { testAccount, txns, asset1 } = assetsData!

#       await subscribeAndVerifyFilter(
#         {
#           type: TransactionType.axfer,
#           sender: testAccount.addr,
#           minAmount: 1,
#           maxAmount: 1,
#           assetId: asset1.assetId,
#         },
#         [extractFromGroupResult(txns, 3)],
#       )
#     })
#   })
def test_multiple_asset_ids(filter_fixture: dict) -> None:
    asset_transfers_data = asset_transfers_fixture()
    test_account = asset_transfers_data['test_account']
    asset1 = asset_transfers_data['asset1']
    asset2 = asset_transfers_data['asset2']
    txns = asset_transfers_data['txns']
    subscribe_and_verify_filter = filter_fixture['subscribe_and_verify_filter']

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'asset_id': [asset1, asset2],
        },
        [txns.tx_ids[0], txns.tx_ids[1], txns.tx_ids[3], txns.tx_ids[4]]
    )

def test_asset_create(filter_fixture: dict) -> None:
    asset_transfers_data = asset_transfers_fixture()
    test_account = asset_transfers_data['test_account']
    txns = asset_transfers_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify']

    subscribe_and_verify(
        {
            'sender': test_account,
            'asset_create': True,
        },
        txns.tx_ids[2]
    )

def test_transaction_types(filter_fixture: dict) -> None:
    asset_transfers_data = asset_transfers_fixture()
    test_account = asset_transfers_data['test_account']
    txns = asset_transfers_data['txns']
    subscribe_and_verify_filter = filter_fixture['subscribe_and_verify_filter']

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'type': 'axfer',
        },
        [txns.tx_ids[0], txns.tx_ids[1], txns.tx_ids[3], txns.tx_ids[4]]
    )

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'type': 'acfg',
        },
        [txns.tx_ids[2]]
    )

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'type': ['acfg', 'axfer'],
        },
        txns.tx_ids
    )

def test_min_amount_of_asset(filter_fixture: dict) -> None:
    asset_transfers_data = asset_transfers_fixture()
    test_account = asset_transfers_data['test_account']
    txns = asset_transfers_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify']

    subscribe_and_verify(
        {
            'type': 'axfer',
            'sender': test_account,
            'min_amount': 2,
        },
        txns.tx_ids[4]
    )

def test_max_amount_of_asset(filter_fixture: dict) -> None:
    asset_transfers_data = asset_transfers_fixture()
    test_account = asset_transfers_data['test_account']
    txns = asset_transfers_data['txns']
    subscribe_and_verify_filter = filter_fixture['subscribe_and_verify_filter']

    subscribe_and_verify_filter(
        {
            'type': 'axfer',
            'sender': test_account,
            'max_amount': 1,
        },
        [txns.tx_ids[0], txns.tx_ids[1], txns.tx_ids[3]]
    )

def test_max_amount_of_asset_with_asset_id(filter_fixture: dict) -> None:
    asset_transfers_data = asset_transfers_fixture()
    test_account = asset_transfers_data['test_account']
    txns = asset_transfers_data['txns']
    asset1 = asset_transfers_data['asset1']
    subscribe_and_verify_filter = filter_fixture['subscribe_and_verify_filter']

    subscribe_and_verify_filter(
        {
            'type': 'axfer',
            'sender': test_account,
            'max_amount': 1,
            'asset_id': asset1,
        },
        [txns.tx_ids[0], txns.tx_ids[3]]
    )

def test_min_and_max_amount_of_asset_with_asset_id(filter_fixture: dict) -> None:
    asset_transfers_data = asset_transfers_fixture()
    test_account = asset_transfers_data['test_account']
    txns = asset_transfers_data['txns']
    asset1 = asset_transfers_data['asset1']
    subscribe_and_verify = filter_fixture['subscribe_and_verify']

    subscribe_and_verify(
        {
            'type': 'axfer',
            'sender': test_account,
            'min_amount': 1,
            'max_amount': 1,
            'asset_id': asset1,
        },
        txns.tx_ids[3]
    )

# describe('App transactions', () => {
#     test('Works for app create', async () => {
#       const { testAccount, txns } = appData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           appCreate: true,
#         },
#         extractFromGroupResult(txns, 2),
#       )
#     })
def test_app_create(filter_fixture: dict) -> None:
    apps_data = apps_fixture()
    test_account = apps_data['test_account']
    txns = apps_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify']

    subscribe_and_verify(
        {
            'sender': test_account,
            'app_create': True,
        },
        txns.tx_ids[2]
    )

#     test('Works for app ID(s)', async () => {
#       const { testAccount, app1, app2, txns } = appData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           appId: Number(app1.creation.confirmation!.applicationIndex!),
#         },
#         [extractFromGroupResult(txns, 0), extractFromGroupResult(txns, 3)],
#       )

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           appId: [Number(app1.creation.confirmation!.applicationIndex!), Number(app2.creation.confirmation!.applicationIndex!)],
#         },
#         [extractFromGroupResult(txns, 0), extractFromGroupResult(txns, 1), extractFromGroupResult(txns, 3)],
#       )
#     })

#     test('Works for on-complete(s)', async () => {
#       const { testAccount, txns } = appData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           appOnComplete: ApplicationOnComplete.optin,
#         },
#         extractFromGroupResult(txns, 3),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           appOnComplete: [ApplicationOnComplete.optin, ApplicationOnComplete.noop],
#         },
#         [
#           extractFromGroupResult(txns, 0),
#           extractFromGroupResult(txns, 1),
#           extractFromGroupResult(txns, 2),
#           extractFromGroupResult(txns, 3),
#         ],
#       )
#     })

#     test('Works for method signature(s)', async () => {
#       const { testAccount, txns } = appData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           methodSignature: 'opt_in()void',
#         },
#         extractFromGroupResult(txns, 3),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           methodSignature: ['opt_in()void', 'madeUpMethod()void'],
#         },
#         extractFromGroupResult(txns, 3),
#       )

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           methodSignature: ['opt_in()void', 'call_abi(string)string'],
#         },
#         [extractFromGroupResult(txns, 0), extractFromGroupResult(txns, 1), extractFromGroupResult(txns, 3)],
#       )
#     })

#     test('Works for app args', async () => {
#       const { testAccount, txns } = appData!

#       await subscribeAndVerifyFilter(
#         {
#           sender: testAccount.addr,
#           // ARC-4 string has first 2 bytes with length of the string so slice them off before comparing
#           appCallArgumentsMatch: (args) => !!args && args.length > 1 && Buffer.from(args[1].slice(2)).toString('utf-8') === 'test1',
#         },
#         extractFromGroupResult(txns, 0),
#       )
#     })
#   })

#   test('Works for custom filter', async () => {
#     const { testAccount, txns } = algoTransfersData!

#     await subscribeAndVerifyFilter(
#       {
#         sender: testAccount.addr,
#         customFilter: (t) => t.id === txns.txIds[1],
#       },
#       extractFromGroupResult(txns, 1),
#     )
#   })
# })
def test_app_ids(filter_fixture: dict) -> None:
    apps_data = apps_fixture()
    test_account = apps_data['test_account']
    app1 = apps_data['app1']
    app2 = apps_data['app2']
    txns = apps_data['txns']
    subscribe_and_verify_filter = filter_fixture['subscribe_and_verify_filter']

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'app_id': app1.app_id,
        },
        [txns.tx_ids[0], txns.tx_ids[3]]
    )

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'app_id': [app1.app_id, app2.app_id],
        },
        [txns.tx_ids[0], txns.tx_ids[1], txns.tx_ids[3]]
    )

def test_on_complete(filter_fixture: dict) -> None:
    apps_data = apps_fixture()
    test_account = apps_data['test_account']
    txns = apps_data['txns']
    subscribe_and_verify_filter = filter_fixture['subscribe_and_verify_filter']

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'app_on_complete': 'optin',
        },
        [txns.tx_ids[3]]
    )

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'app_on_complete': ['optin', 'noop'],
        },
        txns.tx_ids
    )

def test_method_signatures(filter_fixture: dict) -> None:
    apps_data = apps_fixture()
    test_account = apps_data['test_account']
    txns = apps_data['txns']
    subscribe_and_verify_filter = filter_fixture['subscribe_and_verify_filter']

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'method_signature': 'opt_in()void',
        },
        [txns.tx_ids[3]]
    )

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'method_signature': ['opt_in()void', 'madeUpMethod()void'],
        },
        [txns.tx_ids[3]]
    )

    subscribe_and_verify_filter(
        {
            'sender': test_account,
            'method_signature': ['opt_in()void', 'call_abi(string)string'],
        },
        [txns.tx_ids[0], txns.tx_ids[1], txns.tx_ids[3]]
    )

def test_app_args(filter_fixture: dict) -> None:
    apps_data = apps_fixture()
    test_account = apps_data['test_account']
    txns = apps_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify']

    def app_call_arguments_match(args: list) -> bool:
        return (args and len(args) > 1 and
                args[1][2:].decode('utf-8') == 'test1')

    subscribe_and_verify(
        {
            'sender': test_account,
            'app_call_arguments_match': app_call_arguments_match,
        },
        txns.tx_ids[0]
    )

def test_custom_filter(filter_fixture: dict) -> None:
    algo_transfers_data = algo_transfers_fixture()
    test_account = algo_transfers_data['test_account']
    txns = algo_transfers_data['txns']
    subscribe_and_verify = filter_fixture['subscribe_and_verify']

    def custom_filter(t: dict) -> bool:
        return t['id'] == txns.tx_ids[1]

    subscribe_and_verify(
        {
            'sender': test_account,
            'custom_filter': custom_filter,
        },
        txns.tx_ids[1]
    )
