from algokit_subscriber_py.subscriber import AlgorandSubscriber
from algokit_subscriber_py.types.subscription import SubscribedTransaction
from algokit_utils.beta.algorand_client import AlgorandClient

algorand = AlgorandClient.main_net()
watermark = 0

def get_watermark() -> int:
    return watermark

def set_watermark(new_watermark: int) -> None:
    global watermark  # noqa: PLW0603
    watermark = new_watermark

subscriber = AlgorandSubscriber(algod_client=algorand.client.algod, config={
    'filters': [
        {
            'name': 'usdc',
            'filter': {
                'type': 'axfer',
                'asset_id': 31566704, # mainnet usdc
                'min_amount': 1_000_000
            }
        }
    ],
    'wait_for_block_when_at_tip': True,
    'watermark_persistence': {
        'get': get_watermark,
        'set': set_watermark
    },
    'sync_behaviour': 'skip-sync-newest'
})

def print_usdc(transaction: SubscribedTransaction, _: str) -> None:
    axfer = transaction['asset-transfer-transaction']
    print(f"{transaction['sender']} sent {axfer['receiver']} {axfer['amount'] * 1e-6} USDC") # noqa: T201

subscriber.on('usdc', print_usdc)
subscriber.start()
