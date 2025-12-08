import dataclasses

import algokit_utils.applications.app_factory
import pytest
from algokit_indexer_client.models import Transaction
from algokit_transact import AddressWithSigners
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    AssetCreateParams,
    AssetOptInParams,
    AssetTransferParams,
    PaymentParams,
    SendTransactionComposerResults,
)

from algokit_subscriber.types.subscription import TransactionFilter

from .accounts import generate_account
from .conftest import FilterFixture


@dataclasses.dataclass(kw_only=True)
class _AlgoTransfersFixture:
    test_account: str
    account2: str
    account3: AddressWithSigners
    txns: SendTransactionComposerResults


@pytest.fixture
def algo_transfers_fixture(localnet: AlgorandClient) -> _AlgoTransfersFixture:
    test_account = generate_account(localnet, 10_000_000)
    account2 = generate_account(localnet, 3_000_000)
    account3 = localnet.account.random()

    txns = (
        localnet.new_group()
        .add_payment(
            PaymentParams(
                sender=test_account,
                receiver=account2,
                amount=AlgoAmount(micro_algo=1_000_000),
                note=b"a",
            )
        )
        .add_payment(
            PaymentParams(
                sender=test_account,
                receiver=account3.addr,
                amount=AlgoAmount(micro_algo=2_000_000),
                note=b"b",
            )
        )
        .add_payment(
            PaymentParams(
                sender=account2,
                receiver=test_account,
                amount=AlgoAmount(micro_algo=1_000_000),
                note=b"c",
            )
        )
        .send()
    )

    return _AlgoTransfersFixture(
        test_account=test_account,
        account2=account2,
        account3=account3,
        txns=txns,
    )


@dataclasses.dataclass(kw_only=True)
class _AssetTransfersFixture:
    test_account: str
    asset1: int
    asset2: int
    txns: SendTransactionComposerResults


@pytest.fixture
def asset_transfers_fixture(localnet: AlgorandClient) -> _AssetTransfersFixture:
    test_account = generate_account(localnet, 10_000_000)
    asset1 = localnet.send.asset_create(
        AssetCreateParams(sender=test_account, total=100)
    ).confirmation.asset_id
    assert asset1 is not None
    asset2 = localnet.send.asset_create(
        AssetCreateParams(sender=test_account, total=101)
    ).confirmation.asset_id
    assert asset2 is not None
    txns = (
        localnet.new_group()
        .add_asset_opt_in(AssetOptInParams(sender=test_account, asset_id=asset1))
        .add_asset_opt_in(AssetOptInParams(sender=test_account, asset_id=asset2))
        .add_asset_create(AssetCreateParams(sender=test_account, total=103))
        .add_asset_transfer(
            AssetTransferParams(
                sender=test_account, receiver=test_account, asset_id=asset1, amount=1
            )
        )
        .add_asset_transfer(
            AssetTransferParams(
                sender=test_account, receiver=test_account, asset_id=asset1, amount=2
            )
        )
        .send()
    )
    return _AssetTransfersFixture(
        test_account=test_account,
        asset1=asset1,
        asset2=asset2,
        txns=txns,
    )


@dataclasses.dataclass
class _AppsFixture:
    app1: int
    app2: int
    test_account: str
    txns: SendTransactionComposerResults


@pytest.fixture
def apps_fixture(localnet: AlgorandClient, app_factory: algokit_utils.AppFactory) -> _AppsFixture:
    test_account = generate_account(localnet, 10_000_000)
    signer = localnet.account.get_signer(test_account)

    _, app1 = app_factory.send.bare.create(
        algokit_utils.AppFactoryCreateParams(sender=test_account, signer=signer, note=b"1")
    )
    _, app2 = app_factory.send.bare.create(
        algokit_utils.AppFactoryCreateParams(sender=test_account, signer=signer, note=b"2")
    )
    app1_client = app_factory.get_app_client_by_id(
        app1.app_id, default_signer=signer, default_sender=test_account
    )
    app2_client = app_factory.get_app_client_by_id(
        app2.app_id, default_signer=signer, default_sender=test_account
    )

    (app1_call,) = app1_client.create_transaction.call(
        algokit_utils.AppClientMethodCallParams(method="call_abi(string)string", args=["test1"])
    ).transactions
    (app2_call,) = app2_client.create_transaction.call(
        algokit_utils.AppClientMethodCallParams(method="call_abi(string)string", args=["test2"])
    ).transactions
    app_create = app_factory.create_transaction.bare.create(
        algokit_utils.AppFactoryCreateParams(sender=test_account, signer=signer, note=b"3")
    )
    (app1_opt_in,) = app1_client.create_transaction.opt_in(
        algokit_utils.AppClientMethodCallParams(method="opt_in()void")
    ).transactions

    txns = (
        localnet.new_group()
        .add_transaction(app1_call)
        .add_transaction(app2_call)
        .add_transaction(app_create)
        .add_transaction(app1_opt_in)
        .send()
    )

    return _AppsFixture(
        app1=app1.app_id,
        app2=app2.app_id,
        test_account=test_account,
        txns=txns,
    )


def test_single_receiver(
    filter_fixture: FilterFixture, algo_transfers_fixture: _AlgoTransfersFixture
) -> None:
    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            receiver=algo_transfers_fixture.account2,
        ),
        algo_transfers_fixture.txns.tx_ids[0],
    )


def test_single_sender(
    filter_fixture: FilterFixture, algo_transfers_fixture: _AlgoTransfersFixture
) -> None:
    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=algo_transfers_fixture.account2,
        ),
        algo_transfers_fixture.txns.tx_ids[2],
    )


def test_multiple_receivers(
    filter_fixture: FilterFixture, algo_transfers_fixture: _AlgoTransfersFixture
) -> None:
    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            receiver=[
                algo_transfers_fixture.account2,
                algo_transfers_fixture.account3.addr,
            ],
        ),
        algo_transfers_fixture.txns.tx_ids[:2],
    )


def test_multiple_senders(
    filter_fixture: FilterFixture, algo_transfers_fixture: _AlgoTransfersFixture
) -> None:
    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=[
                algo_transfers_fixture.test_account,
                algo_transfers_fixture.account2,
            ],
        ),
        algo_transfers_fixture.txns.tx_ids,
    )


def test_min_amount_of_algos(
    filter_fixture: FilterFixture, algo_transfers_fixture: _AlgoTransfersFixture
) -> None:
    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=algo_transfers_fixture.test_account,
            min_amount=1_000_001,  # 1 Algo + 1 microAlgo
        ),
        algo_transfers_fixture.txns.tx_ids[1],
    )


def test_max_amount_of_algos(
    filter_fixture: FilterFixture, algo_transfers_fixture: _AlgoTransfersFixture
) -> None:
    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=algo_transfers_fixture.test_account,
            max_amount=1_000_001,  # 1 Algo + 1 microAlgo
        ),
        algo_transfers_fixture.txns.tx_ids[0],
    )


def test_note_prefix(
    filter_fixture: FilterFixture, algo_transfers_fixture: _AlgoTransfersFixture
) -> None:
    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=algo_transfers_fixture.test_account,
            note_prefix="a",
        ),
        algo_transfers_fixture.txns.tx_ids[0],
    )

    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=algo_transfers_fixture.test_account,
            note_prefix="b",
        ),
        algo_transfers_fixture.txns.tx_ids[1],
    )


def test_asset_txns(
    filter_fixture: FilterFixture, asset_transfers_fixture: _AssetTransfersFixture
) -> None:
    tx_ids = asset_transfers_fixture.txns.tx_ids

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=asset_transfers_fixture.test_account,
            asset_id=asset_transfers_fixture.asset1,
        ),
        [tx_ids[0], tx_ids[3], tx_ids[4]],
    )


def test_multiple_asset_ids(
    filter_fixture: FilterFixture, asset_transfers_fixture: _AssetTransfersFixture
) -> None:
    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=asset_transfers_fixture.test_account,
            asset_id=[asset_transfers_fixture.asset1, asset_transfers_fixture.asset2],
        ),
        [
            asset_transfers_fixture.txns.tx_ids[0],
            asset_transfers_fixture.txns.tx_ids[1],
            asset_transfers_fixture.txns.tx_ids[3],
            asset_transfers_fixture.txns.tx_ids[4],
        ],
    )


def test_asset_create(
    filter_fixture: FilterFixture, asset_transfers_fixture: _AssetTransfersFixture
) -> None:
    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=asset_transfers_fixture.test_account,
            asset_create=True,
        ),
        asset_transfers_fixture.txns.tx_ids[2],
    )


def test_transaction_types(
    filter_fixture: FilterFixture, asset_transfers_fixture: _AssetTransfersFixture
) -> None:
    tx_ids = asset_transfers_fixture.txns.tx_ids

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=asset_transfers_fixture.test_account,
            type="axfer",
        ),
        [tx_ids[0], tx_ids[1], tx_ids[3], tx_ids[4]],
    )

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=asset_transfers_fixture.test_account,
            type="acfg",
        ),
        [tx_ids[2]],
    )

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=asset_transfers_fixture.test_account,
            type=["acfg", "axfer"],
        ),
        tx_ids,
    )


def test_min_amount_of_asset(
    filter_fixture: FilterFixture, asset_transfers_fixture: _AssetTransfersFixture
) -> None:
    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            type="axfer",
            sender=asset_transfers_fixture.test_account,
            min_amount=2,
        ),
        asset_transfers_fixture.txns.tx_ids[4],
    )


def test_max_amount_of_asset(
    filter_fixture: FilterFixture, asset_transfers_fixture: _AssetTransfersFixture
) -> None:
    tx_ids = asset_transfers_fixture.txns.tx_ids

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            type="axfer",
            sender=asset_transfers_fixture.test_account,
            max_amount=1,
        ),
        [tx_ids[0], tx_ids[1], tx_ids[3]],
    )


def test_max_amount_of_asset_with_asset_id(
    filter_fixture: FilterFixture, asset_transfers_fixture: _AssetTransfersFixture
) -> None:
    tx_ids = asset_transfers_fixture.txns.tx_ids

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            type="axfer",
            sender=asset_transfers_fixture.test_account,
            max_amount=1,
            asset_id=asset_transfers_fixture.asset1,
        ),
        [tx_ids[0], tx_ids[3]],
    )


def test_min_and_max_amount_of_asset_with_asset_id(
    filter_fixture: FilterFixture, asset_transfers_fixture: _AssetTransfersFixture
) -> None:
    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            type="axfer",
            sender=asset_transfers_fixture.test_account,
            min_amount=1,
            max_amount=1,
            asset_id=asset_transfers_fixture.asset1,
        ),
        asset_transfers_fixture.txns.tx_ids[3],
    )


def test_app_create(filter_fixture: FilterFixture, apps_fixture: _AppsFixture) -> None:
    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=apps_fixture.test_account,
            app_create=True,
        ),
        apps_fixture.txns.tx_ids[2],
    )


def test_app_ids(filter_fixture: FilterFixture, apps_fixture: _AppsFixture) -> None:
    tx_ids = apps_fixture.txns.tx_ids

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=apps_fixture.test_account,
            app_id=apps_fixture.app1,
        ),
        [tx_ids[0], tx_ids[3]],
    )

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=apps_fixture.test_account,
            app_id=[apps_fixture.app1, apps_fixture.app2],
        ),
        [tx_ids[0], tx_ids[1], tx_ids[3]],
    )


def test_on_complete(filter_fixture: FilterFixture, apps_fixture: _AppsFixture) -> None:
    tx_ids = apps_fixture.txns.tx_ids

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=apps_fixture.test_account,
            app_on_complete="optin",
        ),
        [tx_ids[3]],
    )

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=apps_fixture.test_account,
            app_on_complete=["optin", "noop"],
        ),
        tx_ids,
    )


def test_method_signatures(filter_fixture: FilterFixture, apps_fixture: _AppsFixture) -> None:
    tx_ids = apps_fixture.txns.tx_ids

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=apps_fixture.test_account,
            method_signature="opt_in()void",
        ),
        [tx_ids[3]],
    )

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=apps_fixture.test_account,
            method_signature=["opt_in()void", "madeUpMethod()void"],
        ),
        [tx_ids[3]],
    )

    filter_fixture.subscribe_and_verify_filter(
        TransactionFilter(
            name="default",
            sender=apps_fixture.test_account,
            method_signature=["opt_in()void", "call_abi(string)string"],
        ),
        [tx_ids[0], tx_ids[1], tx_ids[3]],
    )


def test_app_args(filter_fixture: FilterFixture, apps_fixture: _AppsFixture) -> None:
    def app_call_arguments_match(args: list[bytes] | None) -> bool:
        return bool(args and len(args) > 1 and args[1][2:].decode("utf-8") == "test1")

    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=apps_fixture.test_account,
            app_call_arguments_match=app_call_arguments_match,
        ),
        apps_fixture.txns.tx_ids[0],
    )


def test_custom_filter(
    filter_fixture: FilterFixture, algo_transfers_fixture: _AlgoTransfersFixture
) -> None:
    def custom_filter(t: Transaction) -> bool:
        return t.id_ == algo_transfers_fixture.txns.tx_ids[1]

    filter_fixture.subscribe_and_verify(
        TransactionFilter(
            name="default",
            sender=algo_transfers_fixture.test_account,
            custom_filter=custom_filter,
        ),
        algo_transfers_fixture.txns.tx_ids[1],
    )
