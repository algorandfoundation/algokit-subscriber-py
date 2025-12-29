import base64
import dataclasses
import enum
import json
import time
import typing
from pathlib import Path

import algokit_utils
import pytest
from algokit_indexer_client import IndexerClient
from algokit_indexer_client.exceptions import UnexpectedStatusError
from algokit_transact import AddressWithSigners
from algokit_utils import AlgorandClient
from syrupy import types
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.location import PyTestLocation

from algokit_subscriber.types.arc28 import Arc28EventGroup
from algokit_subscriber.types.subscription import (
    SubscribedTransaction,
    TransactionFilter,
    TransactionSubscriptionParams,
    TransactionSubscriptionResult,
)
from tests.transactions import get_subscribed_transactions_for_test, send_x_transactions


def filter_synthetic_transactions(t: SubscribedTransaction) -> bool:
    return not (
        t.tx_type == "pay" and t.fee == 0 and t.parent_transaction_id is None and t.group is None
    )


def wait_for_round(indexer: IndexerClient, round_num: int) -> None:
    while True:
        try:
            indexer.lookup_block(round_num, header_only=True)
        except UnexpectedStatusError:
            time.sleep(0.2)
        else:
            break


def wait_for_txn(indexer: IndexerClient, tx_id: str) -> None:
    while True:
        try:
            indexer.lookup_transaction_by_id(tx_id)
        except UnexpectedStatusError:
            time.sleep(0.2)
        else:
            break


@pytest.fixture(scope="session")
def dispenser() -> AddressWithSigners:
    # dispenser is session scoped for faster lookup
    localnet = AlgorandClient.default_localnet()
    return localnet.account.localnet_dispenser()


@pytest.fixture
def localnet(dispenser: AddressWithSigners) -> AlgorandClient:
    localnet = AlgorandClient.default_localnet()
    localnet.set_default_validity_window(1000)
    localnet.account.set_signer(dispenser.addr, dispenser.signer)
    return localnet


@pytest.fixture
def mainnet() -> AlgorandClient:
    return AlgorandClient.mainnet()


@pytest.fixture(scope="session")
def dispenser_address(dispenser: AddressWithSigners) -> str:
    return dispenser.addr


@dataclasses.dataclass
class FilterFixture:
    localnet: AlgorandClient
    dispenser: AddressWithSigners

    def subscribe_algod(
        self,
        txn_filter: TransactionFilter,
        confirmed_round: int,
        arc28_events: list[Arc28EventGroup] | None = None,
    ) -> TransactionSubscriptionResult:
        return get_subscribed_transactions_for_test(
            TransactionSubscriptionParams(
                max_indexer_rounds_to_sync=1,
                sync_behaviour="sync-oldest",
                watermark=confirmed_round - 1,
                current_round=confirmed_round,
                filters=[txn_filter],
                arc28_events=arc28_events,
            ),
            algorand=self.localnet,
        )

    def subscribe_indexer(
        self,
        txn_filter: TransactionFilter,
        confirmed_round: int,
        arc28_events: list[Arc28EventGroup] | None = None,
    ) -> TransactionSubscriptionResult:
        send_x_transactions(3, self.dispenser.addr, self.localnet)
        wait_for_round(self.localnet.client.indexer, confirmed_round)

        result = get_subscribed_transactions_for_test(
            TransactionSubscriptionParams(
                max_rounds_to_sync=1,
                sync_behaviour="catchup-with-indexer",
                watermark=confirmed_round - 1,
                current_round=confirmed_round + 1,
                filters=[txn_filter],
                arc28_events=arc28_events,
            ),
            algorand=self.localnet,
        )

        # filter out txns with 0 fee, no parent, and no group
        result.subscribed_transactions = list(
            filter(filter_synthetic_transactions, result.subscribed_transactions)
        )
        return result

    def subscribe_and_verify(
        self,
        txn_filter: TransactionFilter,
        tx_id: str,
        arc28_events: list[Arc28EventGroup] | None = None,
    ) -> TransactionSubscriptionResult:
        confirmed_round = self._confirmed_round(tx_id)

        subscribed = self.subscribe_algod(txn_filter, confirmed_round, arc28_events)
        assert len(subscribed.subscribed_transactions) == 1
        assert subscribed.subscribed_transactions[0].id_ == tx_id
        return subscribed

    def subscribe_and_verify_filter(
        self,
        txn_filter: TransactionFilter,
        tx_ids: list[str] | str,
        arc28_events: list[Arc28EventGroup] | None = None,
    ) -> TransactionSubscriptionResult:
        __tracebackhide__ = True
        if isinstance(tx_ids, str):
            tx_ids = [tx_ids]

        confirmed_round = self._confirmed_round(tx_ids[-1])

        algod = self.subscribe_algod(txn_filter, confirmed_round, arc28_events)
        algod_txns = [s.id_ for s in algod.subscribed_transactions]
        assert algod_txns == tx_ids, "expected algod transaction ids to match"

        indexer = self.subscribe_indexer(txn_filter, confirmed_round, arc28_events)
        indexer_txns = [s.id_ for s in indexer.subscribed_transactions]
        assert indexer_txns == tx_ids, "expected indexer transaction ids to match"

        return algod

    def _confirmed_round(self, tx_id: str) -> int:
        confirmed_round = self.localnet.client.algod.pending_transaction_information(
            tx_id
        ).confirmed_round
        assert confirmed_round is not None, f"transaction {tx_id} not confirmed"
        return confirmed_round


@pytest.fixture
def filter_fixture(localnet: AlgorandClient, dispenser: AddressWithSigners) -> FilterFixture:
    return FilterFixture(localnet, dispenser)


@pytest.fixture
def app_factory(localnet: AlgorandClient) -> algokit_utils.AppFactory:
    app_spec = Path(__file__).parent / "contracts" / "TestingApp.arc32.json"
    return algokit_utils.AppFactory(
        algokit_utils.AppFactoryParams(
            algorand=localnet,
            app_spec=app_spec.read_text("utf-8"),
        )
    )


class _ModuleJSONSnapshotExtension(JSONSnapshotExtension):
    @classmethod
    def get_snapshot_name(
        cls, *, test_location: PyTestLocation, index: types.SnapshotIndex = 0
    ) -> str:
        _ = test_location
        index_suffix = ""
        if isinstance(index, str):
            index_suffix = f"[{index}]"
        elif index:
            index_suffix = f".{index}"
        return f"module{index_suffix}"

    def serialize(
        self,
        data: types.SerializableData,
        *,
        exclude: types.PropertyFilter | None = None,
        include: types.PropertyFilter | None = None,
        matcher: types.PropertyMatcher | None = None,
    ) -> types.SerializedData:
        data_json = dataclass_to_json(data)
        data_json = self._filter(
            data=data_json,
            depth=0,
            path=(),
            exclude=exclude,
            include=include,
            matcher=matcher,
        )
        return json.dumps(data_json, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def dataclass_to_json(obj: typing.Any) -> object:  # noqa: ANN401
    return _convert_data(dataclasses.asdict(obj))


def _convert_data(obj: object) -> object:
    if isinstance(obj, dict):
        return {key: _convert_data(value) for key, value in obj.items() if value is not None}
    elif isinstance(obj, list | tuple):
        return [_convert_data(item) for item in obj if item is not None]
    elif isinstance(obj, enum.Enum):
        return obj.value
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode("ascii")
    else:
        return obj


@pytest.fixture
def module_snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    return snapshot.use_extension(_ModuleJSONSnapshotExtension)
