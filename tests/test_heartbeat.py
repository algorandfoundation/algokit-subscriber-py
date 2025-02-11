from algokit_utils.beta.algorand_client import AlgorandClient
from algokit_subscriber import AlgorandSubscriber
from algokit_subscriber.types.indexer import TransactionResult
from algokit_subscriber.types.subscription import AlgorandSubscriberConfig, NamedTransactionFilter
from algokit_subscriber.types.transaction import TransactionType


def poll_heartbeat_round(use_indexer: bool) -> None:
    algorand = AlgorandClient.main_net()
    hb_round = 46914103
    watermark: int = hb_round - 1
    def get_watermark() -> int | None:
        return watermark

    def set_watermark(n: int) -> None:
        global watermark  # noqa: PLW0603
        watermark = n

    config: AlgorandSubscriberConfig = {
        "filters": [{
            "name": "heartbeat",
            "filter": {
                "type": TransactionType.hb.value,
            },
        }],
        "max_rounds_to_sync": 1,
        "max_indexer_rounds_to_sync": 1,
        "sync_behaviour": "sync-oldest",
        "watermark_persistence": {
            "get": get_watermark,
            "set": set_watermark,
        },
    }

    if use_indexer:
        config["sync_behaviour"] = "catchup-with-indexer"

    subscriber = AlgorandSubscriber(config=config, algod_client=algorand.client.algod, indexer_client=algorand.client.indexer)

    result = subscriber.poll_once()

    assert len(result["subscribed_transactions"]) == 52

def test_algod_heartbeat() -> None:
    poll_heartbeat_round(use_indexer=False)

def test_indexer_heartbeat() -> None:
    poll_heartbeat_round(use_indexer=True)


