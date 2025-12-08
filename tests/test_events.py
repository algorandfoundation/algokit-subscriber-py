import dataclasses
import random

import algokit_transact
import algokit_utils
import pytest
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    PaymentParams,
)

from algokit_subscriber.types.arc28 import (
    Arc28Event,
    Arc28EventArg,
    Arc28EventFilter,
    Arc28EventGroup,
)
from algokit_subscriber.types.subscription import TransactionFilter

from .conftest import FilterFixture

swapped_event = Arc28Event(
    name="Swapped",
    args=[
        Arc28EventArg(name="a", type="uint64"),
        Arc28EventArg(name="b", type="uint64"),
    ],
)


complex_event = Arc28Event(
    name="Complex",
    args=[
        Arc28EventArg(name="array", type="uint32[]"),
        Arc28EventArg(name="int", type="uint64"),
    ],
)


@dataclasses.dataclass
class _TypedApp:
    client: algokit_utils.AppClient
    creator: algokit_utils.AddressWithSigners

    @property
    def id_(self) -> int:
        return self.client.app_id

    def send(self, txn: algokit_transact.Transaction) -> str:
        result = (
            self.client.algorand.send.new_group()
            .add_transaction(txn)
            .send(algokit_utils.SendParams(max_rounds_to_wait=2))
        )
        return result.tx_ids[0]

    def emit_swapped(self, a: int, b: int) -> algokit_transact.Transaction:
        (txn,) = self.client.create_transaction.call(
            algokit_utils.AppClientMethodCallParams(
                method="emitSwapped(uint64,uint64)void",
                args=[a, b],
                note=random.randbytes(8),
            )
        ).transactions
        return txn

    def emit_swapped_twice(self, a: int, b: int) -> algokit_transact.Transaction:
        (txn,) = self.client.create_transaction.call(
            algokit_utils.AppClientMethodCallParams(
                method="emitSwappedTwice(uint64,uint64)void",
                args=[a, b],
                note=random.randbytes(8),
            )
        ).transactions

        return txn

    def emit_complex(self, a: int, b: int, c: list[int]) -> algokit_transact.Transaction:
        (txn,) = self.client.create_transaction.call(
            algokit_utils.AppClientMethodCallParams(
                method="emitComplex(uint64,uint64,uint32[])void",
                args=[a, b, c],
                note=random.randbytes(8),
            )
        ).transactions

        return txn

    def call_abi(self, value: str) -> algokit_transact.Transaction:
        (txn,) = self.client.create_transaction.call(
            algokit_utils.AppClientMethodCallParams(
                method="call_abi(string)string",
                args=[value],
                note=random.randbytes(8),
            )
        ).transactions

        return txn


@pytest.fixture
def app(app_factory: algokit_utils.AppFactory) -> _TypedApp:
    creator = app_factory.algorand.account.localnet_dispenser()
    _, app_txn = app_factory.send.bare.create(
        algokit_utils.AppFactoryCreateParams(sender=creator.addr, signer=creator.signer)
    )
    app_client = app_factory.get_app_client_by_id(
        app_txn.app_id, default_sender=creator.addr, default_signer=creator.signer
    )
    return _TypedApp(app_client, creator)


@pytest.fixture
def call_emit_pay_txn_group(
    localnet: AlgorandClient, app: _TypedApp
) -> algokit_utils.SendTransactionComposerResults:
    pay_txn = localnet.create_transaction.payment(
        PaymentParams(
            amount=AlgoAmount(micro_algo=1_000_000),
            sender=app.creator.addr,
            receiver=app.creator.addr,
        )
    )
    call_txn = app.call_abi("1")
    emit_txn = app.emit_swapped(1, 2)
    return (
        localnet.new_group()
        .add_transaction(call_txn)
        .add_transaction(emit_txn)
        .add_transaction(pay_txn)
        .send()
    )


def test_simple_event(app: _TypedApp, filter_fixture: FilterFixture) -> None:
    txn = app.emit_swapped(a=1, b=2)
    tx_id = app.send(txn)

    subscription = filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            app_id=app.id_,
        ),
        tx_id,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
            ),
        },
    ).subscribed_transactions[0]

    assert len(subscription.arc28_events) == 1
    (arc28_event,) = subscription.arc28_events

    assert arc28_event.args == [1, 2]
    assert arc28_event.args_by_name == {"a": 1, "b": 2}
    assert arc28_event.group == "group1"
    assert arc28_event.event.name == "Swapped"
    assert arc28_event.event.prefix == bytes.fromhex("1ccbd925")
    assert arc28_event.event.signature == "Swapped(uint64,uint64)"


def test_multiple_events(app: _TypedApp, filter_fixture: FilterFixture) -> None:
    txn = app.emit_swapped_twice(a=1, b=2)
    tx_id = app.send(txn)

    subscription = filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            app_id=app.id_,
        ),
        tx_id,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
            ),
        },
    ).subscribed_transactions[0]

    assert len(subscription.arc28_events) == 2
    second_event = subscription.arc28_events[1]
    assert second_event.args_by_name == {"b": 1, "a": 2}
    assert second_event.group == "group1"


def test_app_id_filter_exclusion(app: _TypedApp, filter_fixture: FilterFixture) -> None:
    txn = app.emit_swapped(a=1, b=2)
    tx_id = app.send(txn)

    subscription = filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            app_id=app.id_,
        ),
        tx_id,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
                process_for_app_ids=[app.id_ + 1],
            ),
        },
    ).subscribed_transactions[0]

    assert not subscription.arc28_events


def test_app_predicate_filter_inclusion(app: _TypedApp, filter_fixture: FilterFixture) -> None:
    txn = app.emit_swapped(a=1, b=2)
    tx_id = app.send(txn)

    subscription = filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            app_id=app.id_,
        ),
        tx_id,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
                process_transaction=lambda transaction: transaction.id_ == tx_id,
            ),
        },
    ).subscribed_transactions[0]

    assert len(subscription.arc28_events) == 1


def test_app_predicate_filter_exclusion(app: _TypedApp, filter_fixture: FilterFixture) -> None:
    txn = app.emit_swapped(a=1, b=2)
    tx_id = app.send(txn)

    subscription = filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            app_id=app.id_,
        ),
        tx_id,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
                process_transaction=lambda _: False,
            ),
        },
    ).subscribed_transactions[0]

    assert not subscription.arc28_events


def test_multiple_events_in_group(app: _TypedApp, filter_fixture: FilterFixture) -> None:
    txn = app.emit_complex(a=1, b=2, c=[1, 2, 3])
    tx_id = app.send(txn)

    subscription = filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            app_id=app.id_,
        ),
        tx_id,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event, complex_event],
            ),
        },
    ).subscribed_transactions[0]

    assert len(subscription.arc28_events) == 2

    swapped = subscription.arc28_events[0]
    assert swapped.args == [1, 2]
    assert swapped.args_by_name == {"a": 1, "b": 2}
    assert swapped.group == "group1"
    assert swapped.event.name == "Swapped"
    assert swapped.event.prefix == bytes.fromhex("1ccbd925")
    assert swapped.event.signature == "Swapped(uint64,uint64)"

    complex_ = subscription.arc28_events[1]
    assert complex_.args == [[1, 2, 3], 2]
    assert complex_.args_by_name == {"array": [1, 2, 3], "int": 2}
    assert complex_.group == "group1"
    assert complex_.event.name == "Complex"
    assert complex_.event.prefix == bytes.fromhex("18da5ea7")
    assert complex_.event.signature == "Complex(uint32[],uint64)"


def test_multiple_groups(app: _TypedApp, filter_fixture: FilterFixture) -> None:
    txn = app.emit_complex(a=1, b=2, c=[1, 2, 3])
    tx_id = app.send(txn)

    subscription = filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            app_id=app.id_,
        ),
        tx_id,
        {
            "group1": Arc28EventGroup(
                events=[complex_event],
            ),
            "group2": Arc28EventGroup(
                events=[swapped_event],
            ),
        },
    ).subscribed_transactions[0]

    assert len(subscription.arc28_events) == 2

    swapped = subscription.arc28_events[0]
    assert swapped.event.signature == "Swapped(uint64,uint64)"
    assert swapped.group == "group2"

    complex_ = subscription.arc28_events[1]
    assert complex_.event.signature == "Complex(uint32[],uint64)"
    assert complex_.group == "group1"


def test_arc28_event_subscription(
    app: _TypedApp,
    filter_fixture: FilterFixture,
    call_emit_pay_txn_group: algokit_utils.SendTransactionComposerResults,
) -> None:
    tx_id = call_emit_pay_txn_group.tx_ids[1]
    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            arc28_events=[Arc28EventFilter(event_name="Swapped", group_name="group1")],
        ),
        [tx_id],
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
            ),
        },
    )


def test_arc28_event_subscription_app_id_include(
    app: _TypedApp,
    filter_fixture: FilterFixture,
    call_emit_pay_txn_group: algokit_utils.SendTransactionComposerResults,
) -> None:
    tx_id = call_emit_pay_txn_group.tx_ids[1]

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            arc28_events=[Arc28EventFilter(event_name="Swapped", group_name="group1")],
        ),
        [tx_id],
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
                process_for_app_ids=[app.id_],
            ),
        },
    )


def test_arc28_event_subscription_app_id_exclude(
    app: _TypedApp,
    filter_fixture: FilterFixture,
    call_emit_pay_txn_group: algokit_utils.SendTransactionComposerResults,
) -> None:
    confirmed_round = call_emit_pay_txn_group.confirmations[0].confirmed_round
    assert confirmed_round is not None, "expected confirmation"

    subscription = filter_fixture.subscribe_algod(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            arc28_events=[Arc28EventFilter(event_name="Swapped", group_name="group1")],
        ),
        confirmed_round,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
                process_for_app_ids=[app.id_ + 1],
            ),
        },
    )

    assert len(subscription.subscribed_transactions) == 0

    subscription2 = filter_fixture.subscribe_indexer(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            arc28_events=[Arc28EventFilter(event_name="Swapped", group_name="group1")],
        ),
        confirmed_round,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
                process_for_app_ids=[app.id_ + 1],
            ),
        },
    )

    assert len(subscription2.subscribed_transactions) == 0


def test_arc28_event_subscription_predicate_include(
    app: _TypedApp,
    filter_fixture: FilterFixture,
    call_emit_pay_txn_group: algokit_utils.SendTransactionComposerResults,
) -> None:
    tx_id = call_emit_pay_txn_group.tx_ids[1]
    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            arc28_events=[Arc28EventFilter(event_name="Swapped", group_name="group1")],
        ),
        [tx_id],
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
                process_transaction=lambda transaction: transaction.id_ == tx_id,
            ),
        },
    )


def test_arc28_event_subscription_predicate_exclude(
    app: _TypedApp,
    filter_fixture: FilterFixture,
    call_emit_pay_txn_group: algokit_utils.SendTransactionComposerResults,
) -> None:
    tx_id = call_emit_pay_txn_group.tx_ids[1]
    confirmed_round = call_emit_pay_txn_group.confirmations[0].confirmed_round
    assert confirmed_round is not None, "expected confirmation"

    subscription = filter_fixture.subscribe_algod(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            arc28_events=[Arc28EventFilter(event_name="Swapped", group_name="group1")],
        ),
        confirmed_round,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
                process_transaction=lambda transaction: transaction.id_ != tx_id,
            ),
        },
    )

    assert len(subscription.subscribed_transactions) == 0

    subscription2 = filter_fixture.subscribe_indexer(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            arc28_events=[Arc28EventFilter(event_name="Swapped", group_name="group1")],
        ),
        confirmed_round,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
                process_transaction=lambda transaction: transaction.id_ != tx_id,
            ),
        },
    )

    assert len(subscription2.subscribed_transactions) == 0


def test_arc28_event_subscription_group_validation(
    app: _TypedApp,
    filter_fixture: FilterFixture,
    call_emit_pay_txn_group: algokit_utils.SendTransactionComposerResults,
) -> None:
    tx_id = call_emit_pay_txn_group.tx_ids[1]
    confirmed_round = call_emit_pay_txn_group.confirmations[0].confirmed_round
    assert confirmed_round is not None, "expected confirmation"

    subscription = filter_fixture.subscribe_algod(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            arc28_events=[Arc28EventFilter(event_name="Swapped", group_name="group2")],
        ),
        confirmed_round,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
                process_transaction=lambda transaction: transaction.id_ != tx_id,
            ),
        },
    )

    assert len(subscription.subscribed_transactions) == 0

    subscription2 = filter_fixture.subscribe_indexer(
        TransactionFilter(
            name="default",
            sender=app.creator.addr,
            arc28_events=[Arc28EventFilter(event_name="Swapped", group_name="group2")],
        ),
        confirmed_round,
        {
            "group1": Arc28EventGroup(
                events=[swapped_event],
                process_transaction=lambda transaction: transaction.id_ != tx_id,
            ),
        },
    )

    assert len(subscription2.subscribed_transactions) == 0
