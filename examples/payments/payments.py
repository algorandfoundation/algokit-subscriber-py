from algokit_subscriber_py.subscriber import AlgorandSubscriber
from algokit_subscriber_py.types.subscription import SubscribedTransaction
from algokit_utils.beta.algorand_client import AlgorandClient

algorand = AlgorandClient.main_net()
watermark = 41651683

def get_watermark() -> int:
    return watermark

def set_watermark(new_watermark: int) -> None:
    global watermark  # noqa: PLW0603
    watermark = new_watermark

subscriber = AlgorandSubscriber(
    algod_client=algorand.client.algod,
    indexer_client=algorand.client.indexer,
    config={
    'filters': [
        {
            'name': 'pay txns',
            'filter': {
                'type': 'pay',
                'min_amount': 0
            }
        }
    ],
    'wait_for_block_when_at_tip': True,
    'watermark_persistence': {
        'get': get_watermark,
        'set': set_watermark
    },
    'sync_behaviour': 'catchup-with-indexer'
})

def print_payment(transaction: SubscribedTransaction, _: str) -> None:
    pay = transaction['payment-transaction']
    print(f"{transaction['sender']} sent {pay['receiver']} {pay['amount'] * 1e-6} ALGO") # noqa: T201

subscriber.on('pay txns', print_payment)
subscriber.start()
