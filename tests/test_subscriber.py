import contextlib
import time
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from algokit_utils import AlgorandClient

from algokit_subscriber import AlgorandSubscriber, in_memory_watermark
from algokit_subscriber.types import subscription as sub

from .accounts import generate_account
from .transactions import send_x_transactions


@dataclass
class _Subscription:
    subscriber: AlgorandSubscriber
    subscribed_test_account_txns: list[str]
    _watermark: sub.WatermarkPersistence

    def get_watermark(self) -> int:
        result = self._watermark.get()
        assert result is not None
        return result


def get_subscription(  # noqa: PLR0913
    algorand: AlgorandClient,
    test_account: str,
    *,
    initial_watermark: int = 0,
    max_rounds_to_sync: int = 500,
    sync_behaviour: sub.SyncBehaviour = "sync-oldest",
    frequency_in_seconds: float | None = None,
    wait_for_block_when_at_tip: bool | None = None,
    filters: list[sub.SubscriberConfigFilter] | None = None,
) -> _Subscription:
    watermark = in_memory_watermark(initial_watermark)

    subscribed_txns = list[str]()

    all_filters: list[sub.SubscriberConfigFilter] = [
        sub.SubscriberConfigFilter(name="test-txn", sender=test_account),
        *(filters or []),
    ]

    subscriber = AlgorandSubscriber(
        algod_client=algorand.client.algod,
        indexer_client=algorand.client.indexer,
        config=sub.AlgorandSubscriberConfig(
            filters=all_filters,
            max_rounds_to_sync=max_rounds_to_sync,
            sync_behaviour=sync_behaviour,
            frequency_in_seconds=frequency_in_seconds,
            wait_for_block_when_at_tip=wait_for_block_when_at_tip,
            watermark_persistence=watermark,
        ),
    )
    subscriber.on("test-txn", lambda r, _: subscribed_txns.append(r.id_))
    return _Subscription(
        subscriber=subscriber,
        subscribed_test_account_txns=subscribed_txns,
        _watermark=watermark,
    )


def test_subscribes_correctly_with_poll_once(localnet: AlgorandClient) -> None:
    test_account = generate_account(localnet)
    results = send_x_transactions(1, test_account, localnet)
    last_txn_round = results.last_txn_round
    tx_ids = results.tx_ids
    subscription = get_subscription(localnet, test_account, initial_watermark=last_txn_round - 1)
    subscriber = subscription.subscriber
    subscribed_test_account_txns = subscription.subscribed_test_account_txns
    get_watermark = subscription.get_watermark

    # Initial catch up with indexer
    result = subscriber.poll_once()
    assert subscribed_test_account_txns == tx_ids
    assert get_watermark() >= last_txn_round
    assert result.current_round >= last_txn_round
    assert result.starting_watermark == last_txn_round - 1
    assert result.new_watermark == result.current_round
    assert result.synced_round_range == (last_txn_round, result.current_round)
    assert len(result.subscribed_transactions) == 1
    assert [t.id_ for t in result.subscribed_transactions] == tx_ids

    # Random transaction
    results_2 = send_x_transactions(1, generate_account(localnet, 3 * 10**6), localnet)
    last_txn_round_2 = results_2.last_txn_round
    subscriber.poll_once()
    assert subscribed_test_account_txns == tx_ids
    assert get_watermark() >= last_txn_round_2

    # Another subscribed transaction
    results_3 = send_x_transactions(1, test_account, localnet)
    last_txn_round_3 = results_3.last_txn_round
    tx_ids_3 = results_3.tx_ids
    subscriber.poll_once()
    assert len(subscribed_test_account_txns) == 2
    assert subscribed_test_account_txns[1] == tx_ids_3[0]
    assert get_watermark() >= last_txn_round_3


def test_subscribes_correctly_with_multiple_filters(localnet: AlgorandClient) -> None:  # noqa: PLR0915
    localnet.set_default_validity_window(1000)
    test_account = generate_account(localnet)
    random_account = generate_account(localnet, 3 * 10**6)
    senders = [
        generate_account(localnet, 5 * 10**6),
        generate_account(localnet, 5 * 10**6),
    ]
    sender_1_txn_ids = []
    sender_1_txn_ids_from_batch = list[str]()
    sender_2_rounds = []
    sender_2_rounds_from_batch = list[int]()
    results = send_x_transactions(1, test_account, localnet)
    first_txn_round = results.last_txn_round
    tx_ids = results.tx_ids
    results_1 = send_x_transactions(2, senders[0], localnet)
    tx_ids_1 = results_1.tx_ids
    results_2 = send_x_transactions(2, senders[1], localnet)
    last_txn_round = results_2.last_txn_round
    tx_ids_2 = results_2.tx_ids
    txns_2 = results_2.txns
    subscription = get_subscription(
        localnet,
        test_account,
        max_rounds_to_sync=100,
        filters=[
            sub.SubscriberConfigFilter(
                name="sender1",
                sender=senders[0],
                mapper=lambda txns: [t.id_ for t in txns],
            ),
            sub.SubscriberConfigFilter(
                name="sender2",
                sender=senders[1],
                mapper=lambda txns: [t.confirmed_round for t in txns],
            ),
        ],
        initial_watermark=first_txn_round - 1,
    )
    subscriber = subscription.subscriber
    get_watermark = subscription.get_watermark

    subscriber.on_batch("sender1", lambda r, _: sender_1_txn_ids_from_batch.extend(r))
    subscriber.on("sender1", lambda r, _: sender_1_txn_ids.append(r))
    subscriber.on_batch("sender2", lambda r, _: sender_2_rounds_from_batch.extend(r))
    subscriber.on("sender2", lambda r, _: sender_2_rounds.append(r))

    # Initial catch up
    result = subscriber.poll_once()
    subscribed_txns = result.subscribed_transactions
    assert len(subscribed_txns) == 5
    assert subscribed_txns[0].id_ == tx_ids[0]
    assert subscribed_txns[1].id_ == tx_ids_1[0]
    assert subscribed_txns[2].id_ == tx_ids_1[1]
    assert subscribed_txns[3].id_ == tx_ids_2[0]
    assert subscribed_txns[4].id_ == tx_ids_2[1]
    assert result.current_round >= last_txn_round
    assert result.starting_watermark == first_txn_round - 1
    assert result.new_watermark == result.current_round
    assert get_watermark() >= result.current_round
    assert result.synced_round_range == (first_txn_round, result.current_round)
    assert len(result.subscribed_transactions) == 5
    assert [t.id_ for t in result.subscribed_transactions] == tx_ids + tx_ids_1 + tx_ids_2
    assert sender_1_txn_ids == tx_ids_1
    assert sender_1_txn_ids_from_batch == sender_1_txn_ids
    assert sender_2_rounds == [t.confirmation.confirmed_round for t in txns_2]
    assert sender_2_rounds_from_batch == sender_2_rounds

    # Random transaction
    results_2 = send_x_transactions(1, random_account, localnet)
    sender_1_txn_ids_from_batch = []
    sender_2_rounds_from_batch = []
    result_2 = subscriber.poll_once()
    assert len(result_2.subscribed_transactions) == 0
    assert get_watermark() >= results_2.last_txn_round

    # More subscribed transactions
    results_3 = send_x_transactions(1, test_account, localnet)
    tx_ids_3 = results_3.tx_ids
    results_13 = send_x_transactions(2, senders[0], localnet)
    tx_ids_13 = results_13.tx_ids
    results_23 = send_x_transactions(2, senders[1], localnet)
    last_subscribed_round_3 = results_23.last_txn_round
    tx_ids_23 = results_23.tx_ids
    txns_23 = results_23.txns

    sender_1_txn_ids_from_batch = []
    sender_2_rounds_from_batch = []
    result_3 = subscriber.poll_once()
    subscribed_txns_3 = result_3.subscribed_transactions
    assert len(subscribed_txns_3) == 5
    assert subscribed_txns_3[0].id_ == tx_ids_3[0]
    assert subscribed_txns_3[1].id_ == tx_ids_13[0]
    assert subscribed_txns_3[2].id_ == tx_ids_13[1]
    assert subscribed_txns_3[3].id_ == tx_ids_23[0]
    assert subscribed_txns_3[4].id_ == tx_ids_23[1]
    assert result_3.current_round >= last_subscribed_round_3
    assert result_3.starting_watermark == result_2.new_watermark
    assert result_3.new_watermark == result_3.current_round
    assert get_watermark() >= result_3.current_round
    assert result_3.synced_round_range == (
        result_2.new_watermark + 1,
        result_3.current_round,
    )
    assert len(result_3.subscribed_transactions) == 5
    assert [t.id_ for t in result_3.subscribed_transactions] == tx_ids_3 + tx_ids_13 + tx_ids_23
    assert sender_1_txn_ids == tx_ids_1 + tx_ids_13
    assert len(sender_1_txn_ids_from_batch) == len(tx_ids_13)
    assert sender_1_txn_ids_from_batch == tx_ids_13
    assert sender_2_rounds == [t.confirmation.confirmed_round for t in txns_2] + [
        t.confirmation.confirmed_round for t in txns_23
    ]
    assert sender_2_rounds_from_batch == [t.confirmation.confirmed_round for t in txns_23]


def test_subscribes_correctly_with_regular_intervals_when_started_and_can_be_stopped(
    localnet: AlgorandClient,
) -> None:
    test_account = generate_account(localnet)
    results = send_x_transactions(1, test_account, localnet)
    last_txn_round = results.last_txn_round
    tx_ids = results.tx_ids
    subscription = get_subscription(
        localnet,
        test_account,
        max_rounds_to_sync=1,
        frequency_in_seconds=0.1,
        initial_watermark=last_txn_round - 1,
    )
    subscriber = subscription.subscriber

    @dataclass
    class PollTracker:
        rounds_synced: int = 0
        start_time: float = field(default_factory=time.time)
        poll_count_before_stopping: int = 0
        poll_count_after_stopping: int = 0

        def inspect(self, _: sub.TransactionSubscriptionResult) -> None:
            self.rounds_synced += 1

            # if 5 seconds have passed, stop the subscriber
            if time.time() - self.start_time >= 0.5:
                print("Waited for ~0.5s")
                self.poll_count_before_stopping = self.rounds_synced

                print("Stopping subscriber")
                subscriber.stop("TEST")
                self.poll_count_after_stopping = self.rounds_synced

    tracker = PollTracker()
    print("Starting subscriber")
    subscriber.start(tracker.inspect)

    # Assert
    assert subscription.subscribed_test_account_txns == tx_ids
    assert subscription.get_watermark() >= last_txn_round
    # Polling frequency is 0.1s and we waited ~0.5s, LocalNet latency is low so expect 3-7 polls
    assert tracker.poll_count_before_stopping >= 3
    assert tracker.poll_count_before_stopping <= 7
    # Expect no more than 1 extra poll after we called stop
    assert tracker.poll_count_after_stopping - tracker.poll_count_before_stopping <= 1


def test_waits_until_transaction_appears_by_default_when_started(localnet: AlgorandClient) -> None:
    test_account = generate_account(localnet)
    current_round = localnet.client.algod.status().last_round
    subscription = get_subscription(
        localnet,
        test_account,
        frequency_in_seconds=10,
        wait_for_block_when_at_tip=True,
        sync_behaviour="sync-oldest",
        initial_watermark=current_round - 1,
    )

    @dataclass
    class PollTracker:
        rounds_synced: int = 0
        poll_count_before_issuing: int = 0
        poll_count_after_issuing: int = 0
        last_txn_round = 0
        tx_ids: list[str] = field(default_factory=list)

        # Note: Because the python implementation is fully sync, we need to test this a bit differently
        def inspect(self, r: sub.TransactionSubscriptionResult) -> None:
            self.rounds_synced += 1

            if r.current_round == current_round:
                print("Issuing transaction")
                self.poll_count_before_issuing = self.rounds_synced
                results = send_x_transactions(1, test_account, localnet)

                self.last_txn_round = results.last_txn_round
                self.tx_ids.extend(results.tx_ids)

            if self.last_txn_round and r.current_round >= self.last_txn_round:
                self.poll_count_after_issuing = self.rounds_synced
                print("Stopping subscriber")
                subscription.subscriber.stop("TEST")

    print("Starting subscriber")
    tracker = PollTracker()
    # Note: We might want to think of a better way to handle this within the library, but timing out for a block like this is very unlikely under normal network conditions
    with contextlib.suppress(TimeoutError):
        subscription.subscriber.start(tracker.inspect)

    # Assert
    assert subscription.subscribed_test_account_txns == tracker.tx_ids
    assert subscription.get_watermark() >= tracker.last_txn_round
    # Expect at least 1 poll to have occurred
    assert tracker.poll_count_after_issuing - tracker.poll_count_before_issuing >= 1


def test_correctly_fires_various_on_methods(localnet: AlgorandClient) -> None:
    test_account = generate_account(localnet)
    random_account = generate_account(localnet, 3 * 10**6)
    results = send_x_transactions(2, test_account, localnet)
    txns = results.txns
    tx_ids = results.tx_ids
    results_2 = send_x_transactions(2, random_account, localnet)
    tx_ids_2 = results_2.tx_ids
    confirmed_round = txns[0].confirmation.confirmed_round
    assert confirmed_round is not None
    initial_watermark = confirmed_round - 1
    events_emitted = []

    subscription = get_subscription(
        localnet,
        test_account,
        max_rounds_to_sync=100,
        sync_behaviour="sync-oldest",
        frequency_in_seconds=1000,
        filters=[
            sub.SubscriberConfigFilter(name="account1", sender=test_account),
            sub.SubscriberConfigFilter(name="account2", sender=random_account),
        ],
        initial_watermark=initial_watermark,
    )
    subscriber = subscription.subscriber

    def on_batch_account_1(b: list[sub.SubscribedTransaction], _: str) -> None:
        events_emitted.append(f"batch:account1:{':'.join([t.id_ for t in b])}")

    def on_account_1(t: sub.SubscribedTransaction, _: str) -> None:
        events_emitted.append(f"account1:{t.id_}")

    def on_batch_account_2(b: list[sub.SubscribedTransaction], _: str) -> None:
        events_emitted.append(f"batch:account2:{':'.join([t.id_ for t in b])}")

    def on_account_2(t: sub.SubscribedTransaction, _: str) -> None:
        events_emitted.append(f"account2:{t.id_}")

    def on_before_poll(metadata: sub.BeforePollMetadata, _: str) -> None:
        events_emitted.append(f"before:poll:{metadata.watermark}")

    def on_poll(result: sub.TransactionSubscriptionResult, _: str) -> None:
        events_emitted.append(f"poll:{':'.join([t.id_ for t in result.subscribed_transactions])}")

    def inspect(result: sub.TransactionSubscriptionResult) -> None:
        events_emitted.append(
            f"inspect:{':'.join([t.id_ for t in result.subscribed_transactions])}"
        )
        subscriber.stop("TEST")

    subscriber.on_batch("account1", on_batch_account_1)
    subscriber.on("account1", on_account_1)
    subscriber.on_batch("account2", on_batch_account_2)
    subscriber.on("account2", on_account_2)
    subscriber.on_before_poll(on_before_poll)
    subscriber.on_poll(on_poll)

    subscriber.start(inspect)

    expected_batch_result = f"{tx_ids[0]}:{tx_ids[1]}:{tx_ids_2[0]}:{tx_ids_2[1]}"

    assert events_emitted[0] == f"before:poll:{initial_watermark}"
    assert events_emitted[1] == f"batch:account1:{tx_ids[0]}:{tx_ids[1]}"
    assert events_emitted[2] == f"account1:{tx_ids[0]}"
    assert events_emitted[3] == f"account1:{tx_ids[1]}"
    assert events_emitted[4] == f"batch:account2:{tx_ids_2[0]}:{tx_ids_2[1]}"
    assert events_emitted[5] == f"account2:{tx_ids_2[0]}"
    assert events_emitted[6] == f"account2:{tx_ids_2[1]}"
    assert events_emitted[7] == f"poll:{expected_batch_result}"
    assert events_emitted[8] == f"inspect:{expected_batch_result}"


def test_on_error(localnet: AlgorandClient) -> None:
    subscriber = AlgorandSubscriber(
        algod_client=localnet.client.algod,
        indexer_client=localnet.client.indexer,
        config=sub.AlgorandSubscriberConfig(
            filters=[
                sub.SubscriberConfigFilter(name="pay txns", type="pay", min_amount=0),
            ],
            watermark_persistence=in_memory_watermark(),
            wait_for_block_when_at_tip=True,
            sync_behaviour="catchup-with-indexer",
        ),
    )

    expected_error = Exception("BOOM")

    def raise_error(*_: object) -> None:
        raise expected_error

    subscriber.on("pay txns", raise_error)
    on_error = MagicMock(side_effect=lambda *_: subscriber.stop("TEST"))
    subscriber.on_error(on_error)

    subscriber.start()
    on_error.assert_called_once_with(expected_error, "error")
