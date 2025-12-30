from algokit_transact import TransactionType
from algokit_utils import AlgorandClient

from algokit_subscriber import AlgorandSubscriber
from algokit_subscriber.types.subscription import (
    AlgorandSubscriberConfig,
    SubscriberConfigFilter,
    TransactionFilter,
    WatermarkPersistence,
)


def poll_heartbeat_round(*, use_indexer: bool) -> None:
    algorand = AlgorandClient.mainnet()
    hb_round = 46914103
    watermark: int = hb_round - 1

    def get_watermark() -> int | None:
        return watermark

    def set_watermark(n: int) -> None:
        nonlocal watermark
        watermark = n

    config = AlgorandSubscriberConfig(
        filters=[
            SubscriberConfigFilter(
                name="heartbeat", filter=TransactionFilter(type=TransactionType.Heartbeat.value)
            ),
        ],
        max_rounds_to_sync=1,
        max_indexer_rounds_to_sync=1,
        sync_behaviour="catchup-with-indexer" if use_indexer else "sync-oldest",
        watermark_persistence=WatermarkPersistence(
            get=get_watermark,
            set=set_watermark,
        ),
    )

    subscriber = AlgorandSubscriber(
        config=config,
        algod_client=algorand.client.algod,
        indexer_client=algorand.client.indexer,
    )

    result = subscriber.poll_once()

    assert len(result.subscribed_transactions) == 52


def test_algod_heartbeat() -> None:
    poll_heartbeat_round(use_indexer=False)


def test_indexer_heartbeat() -> None:
    poll_heartbeat_round(use_indexer=True)
