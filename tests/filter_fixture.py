import time

import pytest
from algokit_subscriber.types.subscription import TransactionSubscriptionResult
from algokit_utils.beta.algorand_client import AlgorandClient

from .transactions import get_subscribed_transactions_for_test, send_x_transactions


@pytest.fixture()
def filter_fixture() -> dict:
    localnet = AlgorandClient.default_local_net()
    localnet.set_default_validity_window(1000)

    def subscribe_algod(
        txn_filter: dict, confirmed_round: int, arc28_events: list | None = None
    ) -> TransactionSubscriptionResult:
        return get_subscribed_transactions_for_test(
            {
                "max_rounds_to_sync": 1,
                "sync_behaviour": "sync-oldest",
                "watermark": confirmed_round - 1,
                "current_round": confirmed_round,
                "filters": txn_filter,
                "arc28_events": arc28_events or [],
            },
            algorand=localnet,
        )

    def subscribe_indexer(
        txn_filter: dict, confirmed_round: int, arc28_events: list | None = None
    ) -> TransactionSubscriptionResult:
        send_x_transactions(2, localnet.account.localnet_dispenser().address, localnet)
        while True:
            try:
                localnet.client.indexer.block_info(confirmed_round)
                break
            except Exception:
                print(
                    f"Waiting for round {confirmed_round} to be available on indexer..."
                )
                time.sleep(1)

        return get_subscribed_transactions_for_test(
            {
                "max_rounds_to_sync": 1,
                "sync_behaviour": "catchup-with-indexer",
                "watermark": confirmed_round - 1,
                "current_round": confirmed_round + 1,
                "filters": txn_filter,
                "arc28_events": arc28_events or [],
            },
            algorand=localnet,
        )

    def subscribe_and_verify(
        txn_filter: dict, tx_id: str, arc28_events: list | None = None
    ) -> TransactionSubscriptionResult:
        confirmed_round = localnet.client.algod.pending_transaction_info(tx_id)[
            "confirmed-round"
        ]

        subscribed = subscribe_algod(txn_filter, confirmed_round, arc28_events)
        assert len(subscribed["subscribed_transactions"]) == 1
        assert subscribed["subscribed_transactions"][0]["id"] == tx_id
        return subscribed

    def subscribe_and_verify_filter(
        txn_filter: dict, tx_ids: list[str] | str, arc28_events: list | None = None
    ) -> dict:
        if isinstance(tx_ids, str):
            tx_ids = [tx_ids]

        confirmed_round = localnet.client.algod.pending_transaction_info(tx_ids[-1])[
            "confirmed-round"
        ]

        algod = subscribe_algod(txn_filter, confirmed_round, arc28_events)
        assert len(algod["subscribed_transactions"]) == len(tx_ids)
        assert [s["id"] for s in algod["subscribed_transactions"]] == tx_ids

        indexer = subscribe_indexer(txn_filter, confirmed_round, arc28_events)
        assert len(indexer["subscribed_transactions"]) == len(tx_ids)
        assert [s["id"] for s in indexer["subscribed_transactions"]] == tx_ids

        return {
            "algod": algod,
            # "indexer": indexer
        }

    return {
        "localnet": localnet,
        "subscribe_algod": subscribe_algod,
        "subscribe_indexer": subscribe_indexer,
        "subscribe_and_verify": subscribe_and_verify,
        "subscribe_and_verify_filter": subscribe_and_verify_filter,
    }
