
import time
from typing import cast
from unittest.mock import MagicMock

from algokit_subscriber_py.subscription import get_subscribed_transactions
from algokit_subscriber_py.types.subscription import TransactionSubscriptionResult
from algokit_utils.beta.algorand_client import AlgorandClient
from algokit_utils.beta.composer import PayParams


def send_x_transactions(x: int, sender: str, algorand: AlgorandClient ) -> dict:
    txns = []
    rounds: list[int] = []
    tx_ids: list[str] = []
    for i in range(x):
        txns.append(algorand.send.payment(PayParams(
            sender=sender,
            receiver=sender,
            amount=0,
            note=f"{i} {time.time()}".encode()
        )))

        rounds.append(txns[-1]['confirmation']['confirmed-round'])
        tx_ids.append(txns[-1]['tx_id'])

    last_txn_round = rounds[-1]

    return {
        "txns": txns,
        "rounds": rounds,
        "last_txn_round": last_txn_round,
        "tx_ids": tx_ids
    }

def get_subscribed_transactions_for_test(sub_info: dict, algorand: AlgorandClient) -> TransactionSubscriptionResult:
    algod = algorand.client.algod

    # Store the original status method
    existing_status = algod.status

    # Create a new mock function
    def mock_status() -> dict:
        # Call the original status method and get its result
        status = cast(dict, existing_status())

        # Modify the 'last-round' key
        status['last-round'] = sub_info['current_round']

        return status

    # Create a MagicMock and set its side_effect to our mock_status function
    mock = MagicMock(side_effect=mock_status)

    # Replace the original status method with our mock
    algod.status = mock # type: ignore[method-assign]

    filters = sub_info["filters"]

    if not isinstance(sub_info["filters"], list):
        filters = [{"name": "default", "filter": sub_info["filters"]}]

    return get_subscribed_transactions(
        subscription={
            "filters": filters,
            "max_rounds_to_sync": sub_info["rounds_to_sync"],
            "max_indexer_rounds_to_sync": sub_info.get("indexer_rounds_to_sync"),
            "sync_behaviour": sub_info["sync_behaviour"],
            "watermark": sub_info.get("watermark", 0),
            "arc28_events": sub_info.get("arc28_events", []),
        },
        algod=algod,
        indexer=algorand.client.indexer
    )

def get_subscribe_transactions_from_sender(subscription: dict, account: str | list[str], algorand: AlgorandClient) -> TransactionSubscriptionResult:
    return get_subscribed_transactions(
        subscription={
            **subscription, # type: ignore[typeddict-item]
            "filters": [
                {
                    "name": a,
                    "filter": {
                        "sender": a
                    }
                } for a in (account if isinstance(account, list) else [account])
            ]
        },
        algod=algorand.client.algod,
        indexer=algorand.client.indexer
    )

def get_confirmations(algorand: AlgorandClient, txids: list[str]) -> list[dict]:
    return [cast(dict, algorand.client.algod.pending_transaction_info(txid)) for txid in txids]
