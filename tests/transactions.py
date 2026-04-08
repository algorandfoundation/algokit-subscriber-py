import dataclasses
import time
from functools import cached_property

from algokit_algod_client.models import NodeStatusResponse, PendingTransactionResponse
from algokit_utils import (
    AlgoAmount,
    AlgorandClient,
    PaymentParams,
    SendSingleTransactionResult,
)

from algokit_subscriber import get_subscribed_transactions
from algokit_subscriber.types.subscription import (
    NamedTransactionFilter,
    SyncBehaviour,
    TransactionFilter,
    TransactionSubscriptionParams,
    TransactionSubscriptionResult,
)


@dataclasses.dataclass
class SendTransactionsResult:
    txns: list[SendSingleTransactionResult]

    @cached_property
    def rounds(self) -> list[int]:
        return [_not_none(txn.confirmation.confirmed_round) for txn in self.txns]

    @cached_property
    def tx_ids(self) -> list[str]:
        return [_not_none(txn.tx_id) for txn in self.txns]

    @property
    def last_txn_round(self) -> int:
        return self.rounds[-1]


def _not_none[T](val: T | None) -> T:
    assert val is not None
    return val


def send_x_transactions(x: int, sender: str, algorand: AlgorandClient) -> SendTransactionsResult:
    txns = [
        algorand.send.payment(
            PaymentParams(
                sender=sender,
                receiver=sender,
                amount=AlgoAmount(micro_algo=0),
                note=f"{i} {time.time()}".encode(),
            )
        )
        for i in range(x)
    ]

    return SendTransactionsResult(txns=txns)


def get_subscribed_transactions_for_test(
    subscription: TransactionSubscriptionParams, algorand: AlgorandClient
) -> TransactionSubscriptionResult:
    algod = algorand.client.algod
    original_status = algod.status

    # Create a new mock function
    def mock_status() -> NodeStatusResponse:
        # Call the original status method and get its result
        result = original_status()

        # Modify the 'last-round' key
        return dataclasses.replace(
            result,
            last_round=subscription.current_round or result.last_round,
        )

    # Replace the original status method with our mock
    algod.status = mock_status  # type: ignore[method-assign]

    return get_subscribed_transactions(
        subscription=subscription,
        algod=algod,
        indexer=algorand.client.indexer,
    )


def get_subscribe_transactions_from_sender(  # noqa: PLR0913
    algorand: AlgorandClient,
    account: str | list[str],
    *,
    sync_behaviour: SyncBehaviour,
    max_rounds_to_sync: int = 500,
    watermark: int = 0,
    max_indexer_rounds_to_sync: int | None = None,
) -> TransactionSubscriptionResult:
    accounts = account if isinstance(account, list) else [account]
    filters = [
        NamedTransactionFilter(name=a, filter=TransactionFilter(sender=a)) for a in accounts
    ]
    return get_subscribed_transactions(
        subscription=TransactionSubscriptionParams(
            filters=filters,
            max_rounds_to_sync=max_rounds_to_sync,
            max_indexer_rounds_to_sync=max_indexer_rounds_to_sync,
            sync_behaviour=sync_behaviour,
            watermark=watermark,
        ),
        algod=algorand.client.algod,
        indexer=algorand.client.indexer,
    )


def get_confirmations(
    algorand: AlgorandClient, tx_ids: list[str]
) -> list[PendingTransactionResponse]:
    return [algorand.client.algod.pending_transaction_information(tx_id) for tx_id in tx_ids]


def remove_none_values[T](obj: T) -> T:
    if isinstance(obj, dict):
        return {key: remove_none_values(value) for key, value in obj.items() if value is not None}  # type: ignore[return-value]
    elif isinstance(obj, list):
        return [remove_none_values(item) for item in obj if item is not None]  # type: ignore[return-value]
    else:
        return obj
