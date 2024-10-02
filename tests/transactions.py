import base64
import time
from typing import cast
from unittest.mock import MagicMock

from algokit_subscriber.subscription import get_subscribed_transactions
from algokit_subscriber.types.block import TransactionInBlock
from algokit_subscriber.types.subscription import TransactionSubscriptionResult
from algokit_subscriber.types.transaction import Transaction
from algokit_subscriber.utils import encode_address
from algokit_utils.beta.algorand_client import AlgorandClient
from algokit_utils.beta.composer import PayParams


def send_x_transactions(x: int, sender: str, algorand: AlgorandClient) -> dict:
    txns = []
    rounds: list[int] = []
    tx_ids: list[str] = []
    for i in range(x):
        txns.append(
            algorand.send.payment(
                PayParams(
                    sender=sender,
                    receiver=sender,
                    amount=0,
                    note=f"{i} {time.time()}".encode(),
                )
            )
        )

        rounds.append(txns[-1]["confirmation"]["confirmed-round"])
        tx_ids.append(txns[-1]["tx_id"])

    last_txn_round = rounds[-1]

    return {
        "txns": txns,
        "rounds": rounds,
        "last_txn_round": last_txn_round,
        "tx_ids": tx_ids,
    }


def get_subscribed_transactions_for_test(
    sub_info: dict, algorand: AlgorandClient
) -> TransactionSubscriptionResult:
    algod = algorand.client.algod

    # Store the original status method
    existing_status = algod.status

    # Create a new mock function
    def mock_status() -> dict:
        # Call the original status method and get its result
        status = cast(dict, existing_status())

        # Modify the 'last-round' key
        status["last-round"] = sub_info["current_round"]

        return status

    # Create a MagicMock and set its side_effect to our mock_status function
    mock = MagicMock(side_effect=mock_status)

    # Replace the original status method with our mock
    algod.status = mock  # type: ignore[method-assign]

    filters = sub_info["filters"]

    if not isinstance(sub_info["filters"], list):
        filters = [{"name": "default", "filter": sub_info["filters"]}]

    return get_subscribed_transactions(
        subscription={
            "filters": filters,
            "max_rounds_to_sync": sub_info["max_rounds_to_sync"],
            "max_indexer_rounds_to_sync": sub_info.get("max_indexer_rounds_to_sync"),
            "sync_behaviour": sub_info["sync_behaviour"],
            "watermark": sub_info.get("watermark", 0),
            "arc28_events": sub_info.get("arc28_events", []),
        },
        algod=algod,
        indexer=algorand.client.indexer,
    )


def get_subscribe_transactions_from_sender(
    subscription: dict, account: str | list[str], algorand: AlgorandClient
) -> TransactionSubscriptionResult:
    return get_subscribed_transactions(
        subscription={
            **subscription,  # type: ignore[typeddict-item]
            "filters": [
                {"name": a, "filter": {"sender": a}}
                for a in (account if isinstance(account, list) else [account])
            ],
        },
        algod=algorand.client.algod,
        indexer=algorand.client.indexer,
    )


def get_confirmations(algorand: AlgorandClient, txids: list[str]) -> list[dict]:
    return [
        cast(dict, algorand.client.algod.pending_transaction_info(txid))
        for txid in txids
    ]


def get_transaction_in_block_for_diff(transaction: TransactionInBlock) -> dict:
    return {
        "transaction": get_transaction_for_diff(transaction["transaction"]),
        "parent_offset": transaction.get("parent_offset"),
        "parent_transaction_id": transaction.get("parent_transaction_id"),
        "round_index": transaction["round_index"],
        "round_offset": transaction["round_offset"],
        "created_app_id": transaction.get("created_app_id"),
        "created_asset_id": transaction.get("created_asset_id"),
        "asset_close_amount": transaction.get("asset_close_amount"),
        "close_amount": transaction.get("close_amount"),
    }


def get_transaction_for_diff(transaction: Transaction) -> dict:
    t = {
        **transaction,
        "name": None,
        "app_accounts": [
            encode_address(a.public_key) for a in transaction.get("app_accounts", [])
        ],
        "from": encode_address(transaction["from"].public_key),
        "to": (
            encode_address(transaction["to"].public_key)
            if transaction.get("to")
            else None
        ),
        "rekey_to": (
            encode_address(transaction["rekey_to"].public_key)
            if transaction.get("rekey_to")
            else None
        ),
        "app_args": [
            base64.b64encode(a).decode("utf-8") for a in transaction.get("app_args", [])
        ],
        "genesis_hash": base64.b64encode(transaction["genesis_hash"]).decode("utf-8"),
        "group": (
            base64.b64encode(transaction["group"]).decode("utf-8")
            if transaction.get("group")
            else None
        ),
        "lease": (
            base64.b64encode(transaction["lease"]).decode("utf-8")
            if transaction.get("lease")
            else None
        ),
        "note": (
            base64.b64encode(transaction["note"]).decode("utf-8")
            if transaction.get("note")
            else None
        ),
        "tag": base64.b64encode(transaction["tag"]).decode("utf-8"),
    }

    return clear_undefineds(t)


def clear_undefineds(obj: dict) -> dict:
    return {
        k: clear_undefineds(v) if isinstance(v, dict) else v
        for k, v in obj.items()
        if v is not None
    }


def remove_none_values(obj):  # noqa: ANN201, ANN001
    if isinstance(obj, dict):
        return {
            key: remove_none_values(value)
            for key, value in obj.items()
            if value is not None
        }
    elif isinstance(obj, list):
        return [remove_none_values(item) for item in obj if item is not None]
    else:
        return obj
