from algokit_subscriber.types.arc28 import Arc28Event
from algokit_utils.beta.algorand_client import AlgorandClient
from algokit_utils.beta.composer import PayParams
from algosdk.atomic_transaction_composer import TransactionWithSigner

from .contracts.testing_app_client import TestingAppClient
from .filter_fixture import filter_fixture  # noqa: F401

swapped_event = Arc28Event(
    name="Swapped",
    args=[
        {"name": "a", "type": "uint64"},
        {"name": "b", "type": "uint64"},
    ],
)


complex_event = Arc28Event(
    name="Complex",
    args=[
        {"name": "array", "type": "uint32[]"},
        {"name": "int", "type": "uint64"},
    ],
)


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
        "creation": creation,
    }


def test_simple_event(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    app1 = app(localnet, test_account.address, create=True)
    txn = app1["app"].emit_swapped(a=1, b=2)

    subscription = filter_fixture["subscribe_and_verify"](
        {
            "sender": test_account.address,
            "app_id": app1["creation"]["application-index"],
        },
        txn.tx_id,
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
            },
        ],
    )["subscribed_transactions"][0]

    assert subscription["arc28_events"]
    assert len(subscription["arc28_events"]) == 1
    assert subscription["arc28_events"][0]["args"]
    assert len(subscription["arc28_events"][0]["args"]) == 2
    assert subscription["arc28_events"][0]["args"][0] == 1
    assert subscription["arc28_events"][0]["args"][1] == 2
    assert subscription["arc28_events"][0]["args_by_name"] == {"a": 1, "b": 2}
    assert subscription["arc28_events"][0]["event_name"] == "Swapped"
    assert subscription["arc28_events"][0]["event_prefix"] == "1ccbd925"
    assert (
        subscription["arc28_events"][0]["event_signature"] == "Swapped(uint64,uint64)"
    )
    assert subscription["arc28_events"][0]["group_name"] == "group1"


def test_multiple_events(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    app1 = app(localnet, test_account.address, create=True)
    txn = app1["app"].emit_swapped_twice(a=1, b=2)

    subscription = filter_fixture["subscribe_and_verify"](
        {
            "sender": test_account.address,
            "app_id": app1["creation"]["application-index"],
        },
        txn.tx_id,
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
            },
        ],
    )["subscribed_transactions"][0]

    assert subscription["arc28_events"]
    assert len(subscription["arc28_events"]) == 2
    assert subscription["arc28_events"][1]["args_by_name"] == {"b": 1, "a": 2}
    assert subscription["arc28_events"][1]["group_name"] == "group1"


def test_app_id_filter_exclusion(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    app1 = app(localnet, test_account.address, create=True)
    txn = app1["app"].emit_swapped(a=1, b=2)

    subscription = filter_fixture["subscribe_and_verify"](
        {
            "sender": test_account.address,
            "app_id": app1["creation"]["application-index"],
        },
        txn.tx_id,
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
                "process_for_app_ids": [app1["creation"]["application-index"] + 1],
            },
        ],
    )["subscribed_transactions"][0]

    assert not subscription["arc28_events"]


def test_app_predicate_filter_inclusion(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    app1 = app(localnet, test_account.address, create=True)
    txn = app1["app"].emit_swapped(a=1, b=2)

    subscription = filter_fixture["subscribe_and_verify"](
        {
            "sender": test_account.address,
            "app_id": app1["creation"]["application-index"],
        },
        txn.tx_id,
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
                "process_transaction": lambda transaction: transaction["id"]
                == txn.tx_id,
            },
        ],
    )["subscribed_transactions"][0]

    assert subscription["arc28_events"]
    assert len(subscription["arc28_events"]) == 1


def test_app_predicate_filter_exclusion(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    app1 = app(localnet, test_account.address, create=True)
    txn = app1["app"].emit_swapped(a=1, b=2)

    subscription = filter_fixture["subscribe_and_verify"](
        {
            "sender": test_account.address,
            "app_id": app1["creation"]["application-index"],
        },
        txn.tx_id,
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
                "process_transaction": lambda _: False,
            },
        ],
    )["subscribed_transactions"][0]

    assert not subscription["arc28_events"]


def test_multiple_events_in_group(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    app1 = app(localnet, test_account.address, create=True)
    txn = app1["app"].emit_complex(a=1, b=2, array=[1, 2, 3])

    subscription = filter_fixture["subscribe_and_verify"](
        {
            "sender": test_account.address,
            "app_id": app1["creation"]["application-index"],
        },
        txn.tx_id,
        [
            {
                "group_name": "group1",
                "events": [swapped_event, complex_event],
            },
        ],
    )["subscribed_transactions"][0]

    assert subscription["arc28_events"]
    assert len(subscription["arc28_events"]) == 2

    assert len(subscription["arc28_events"][0]["args"]) == 2
    assert subscription["arc28_events"][0]["args"][0] == 1
    assert subscription["arc28_events"][0]["args"][1] == 2
    assert subscription["arc28_events"][0]["args_by_name"] == {"a": 1, "b": 2}
    assert subscription["arc28_events"][0]["event_name"] == "Swapped"
    assert subscription["arc28_events"][0]["event_prefix"] == "1ccbd925"
    assert (
        subscription["arc28_events"][0]["event_signature"] == "Swapped(uint64,uint64)"
    )
    assert subscription["arc28_events"][0]["group_name"] == "group1"

    assert len(subscription["arc28_events"][1]["args"]) == 2
    assert subscription["arc28_events"][1]["args"][0] == [1, 2, 3]
    assert subscription["arc28_events"][1]["args"][1] == 2
    assert subscription["arc28_events"][1]["args_by_name"] == {
        "array": [1, 2, 3],
        "int": 2,
    }
    assert subscription["arc28_events"][1]["event_name"] == "Complex"
    assert subscription["arc28_events"][1]["event_prefix"] == "18da5ea7"
    assert (
        subscription["arc28_events"][1]["event_signature"] == "Complex(uint32[],uint64)"
    )
    assert subscription["arc28_events"][1]["group_name"] == "group1"


def test_multiple_groups(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    app1 = app(localnet, test_account.address, create=True)
    txn = app1["app"].emit_complex(a=1, b=2, array=[1, 2, 3])

    subscription = filter_fixture["subscribe_and_verify"](
        {
            "sender": test_account.address,
            "app_id": app1["creation"]["application-index"],
        },
        txn.tx_id,
        [
            {
                "group_name": "group1",
                "events": [complex_event],
            },
            {
                "group_name": "group2",
                "events": [swapped_event],
            },
        ],
    )["subscribed_transactions"][0]

    assert subscription["arc28_events"]
    assert len(subscription["arc28_events"]) == 2

    assert (
        subscription["arc28_events"][0]["event_signature"] == "Swapped(uint64,uint64)"
    )
    assert subscription["arc28_events"][0]["group_name"] == "group2"

    assert (
        subscription["arc28_events"][1]["event_signature"] == "Complex(uint32[],uint64)"
    )
    assert subscription["arc28_events"][1]["group_name"] == "group1"


def test_arc28_event_subscription(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    pay_txn = localnet.transactions.payment(
        PayParams(
            amount=1_000_000, sender=test_account.address, receiver=test_account.address
        )
    )
    pay_txn_w_signer = TransactionWithSigner(
        txn=pay_txn, signer=localnet.account.get_signer(test_account.address)
    )

    app1 = app(localnet, test_account.address, create=True)["app"]
    atc = app1.compose().call_abi(value="1").emit_swapped(a=1, b=2).atc
    atc.add_transaction(pay_txn_w_signer)
    txns = localnet.new_group().add_atc(atc).execute()
    filter_fixture["subscribe_and_verify_filter"](
        {
            "sender": test_account.address,
            "arc28_events": [{"event_name": "Swapped", "group_name": "group1"}],
        },
        txns.tx_ids[1],
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
            },
        ],
    )


def test_arc28_event_subscription_app_id_include(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    pay_txn = localnet.transactions.payment(
        PayParams(
            amount=1_000_000, sender=test_account.address, receiver=test_account.address
        )
    )
    pay_txn_w_signer = TransactionWithSigner(
        txn=pay_txn, signer=localnet.account.get_signer(test_account.address)
    )

    app1 = app(localnet, test_account.address, create=True)
    atc = app1["app"].compose().call_abi(value="1").emit_swapped(a=1, b=2).atc
    atc.add_transaction(pay_txn_w_signer)
    txns = localnet.new_group().add_atc(atc).execute()

    filter_fixture["subscribe_and_verify_filter"](
        {
            "sender": test_account.address,
            "arc28_events": [{"event_name": "Swapped", "group_name": "group1"}],
        },
        txns.tx_ids[1],
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
                "process_for_app_ids": [app1["creation"]["application-index"]],
            },
        ],
    )


def test_arc28_event_subscription_app_id_exclude(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    pay_txn = localnet.transactions.payment(
        PayParams(
            amount=1_000_000, sender=test_account.address, receiver=test_account.address
        )
    )
    pay_txn_w_signer = TransactionWithSigner(
        txn=pay_txn, signer=localnet.account.get_signer(test_account.address)
    )

    app1 = app(localnet, test_account.address, create=True)
    atc = app1["app"].compose().call_abi(value="1").emit_swapped(a=1, b=2).atc
    atc.add_transaction(pay_txn_w_signer)
    txns = localnet.new_group().add_atc(atc).execute()

    subscription = filter_fixture["subscribe_algod"](
        {
            "sender": test_account.address,
            "arc28_events": [{"event_name": "Swapped", "group_name": "group1"}],
        },
        txns.confirmed_round,
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
                "process_for_app_ids": [app1["creation"]["application-index"] + 1],
            },
        ],
    )

    assert len(subscription["subscribed_transactions"]) == 0

    subscription2 = filter_fixture["subscribe_indexer"](
        {
            "sender": test_account.address,
            "arc28_events": [{"event_name": "Swapped", "group_name": "group1"}],
        },
        localnet.client.algod.pending_transaction_info(txns.tx_ids[0])[
            "confirmed-round"
        ],
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
                "process_for_app_ids": [app1["creation"]["application-index"] + 1],
            },
        ],
    )

    assert len(subscription2["subscribed_transactions"]) == 0


def test_arc28_event_subscription_predicate_include(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    pay_txn = localnet.transactions.payment(
        PayParams(
            amount=1_000_000, sender=test_account.address, receiver=test_account.address
        )
    )
    pay_txn_w_signer = TransactionWithSigner(
        txn=pay_txn, signer=localnet.account.get_signer(test_account.address)
    )

    app1 = app(localnet, test_account.address, create=True)
    atc = app1["app"].compose().call_abi(value="1").emit_swapped(a=1, b=2).atc
    atc.add_transaction(pay_txn_w_signer)
    txns = localnet.new_group().add_atc(atc).execute()

    filter_fixture["subscribe_and_verify_filter"](
        {
            "sender": test_account.address,
            "arc28_events": [{"event_name": "Swapped", "group_name": "group1"}],
        },
        txns.tx_ids[1],
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
                "process_transaction": lambda transaction: transaction["id"]
                == txns.tx_ids[1],
            },
        ],
    )


def test_arc28_event_subscription_predicate_exclude(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    pay_txn = localnet.transactions.payment(
        PayParams(
            amount=1_000_000, sender=test_account.address, receiver=test_account.address
        )
    )
    pay_txn_w_signer = TransactionWithSigner(
        txn=pay_txn, signer=localnet.account.get_signer(test_account.address)
    )

    app1 = app(localnet, test_account.address, create=True)
    atc = app1["app"].compose().call_abi(value="1").emit_swapped(a=1, b=2).atc
    atc.add_transaction(pay_txn_w_signer)
    txns = localnet.new_group().add_atc(atc).execute()

    subscription = filter_fixture["subscribe_algod"](
        {
            "sender": test_account.address,
            "arc28_events": [{"event_name": "Swapped", "group_name": "group1"}],
        },
        txns.confirmed_round,
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
                "process_transaction": lambda transaction: transaction["id"]
                != txns.tx_ids[1],
            },
        ],
    )

    assert len(subscription["subscribed_transactions"]) == 0

    subscription2 = filter_fixture["subscribe_indexer"](
        {
            "sender": test_account.address,
            "arc28_events": [{"event_name": "Swapped", "group_name": "group1"}],
        },
        localnet.client.algod.pending_transaction_info(txns.tx_ids[0])[
            "confirmed-round"
        ],
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
                "process_transaction": lambda transaction: transaction["id"]
                != txns.tx_ids[1],
            },
        ],
    )

    assert len(subscription2["subscribed_transactions"]) == 0


def test_arc28_event_subscription_group_validation(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    test_account = localnet.account.localnet_dispenser()

    pay_txn = localnet.transactions.payment(
        PayParams(
            amount=1_000_000, sender=test_account.address, receiver=test_account.address
        )
    )
    pay_txn_w_signer = TransactionWithSigner(
        txn=pay_txn, signer=localnet.account.get_signer(test_account.address)
    )

    app1 = app(localnet, test_account.address, create=True)
    atc = app1["app"].compose().call_abi(value="1").emit_swapped(a=1, b=2).atc
    atc.add_transaction(pay_txn_w_signer)
    txns = localnet.new_group().add_atc(atc).execute()

    subscription = filter_fixture["subscribe_algod"](
        {
            "sender": test_account.address,
            "arc28_events": [{"event_name": "Swapped", "group_name": "group2"}],
        },
        txns.confirmed_round,
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
                "process_transaction": lambda transaction: transaction["id"]
                != txns.tx_ids[1],
            },
        ],
    )

    assert len(subscription["subscribed_transactions"]) == 0

    subscription2 = filter_fixture["subscribe_indexer"](
        {
            "sender": test_account.address,
            "arc28_events": [{"event_name": "Swapped", "group_name": "group2"}],
        },
        localnet.client.algod.pending_transaction_info(txns.tx_ids[0])[
            "confirmed-round"
        ],
        [
            {
                "group_name": "group1",
                "events": [swapped_event],
                "process_transaction": lambda transaction: transaction["id"]
                != txns.tx_ids[1],
            },
        ],
    )

    assert len(subscription2["subscribed_transactions"]) == 0
