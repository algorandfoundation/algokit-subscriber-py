import pytest
from algokit_subscriber.types.subscription import BalanceChangeRole
from algokit_utils.beta.algorand_client import AlgorandClient

from .transactions import (
    get_subscribed_transactions_for_test,
    remove_none_values,
)

NESTED_INNER_ROUND = 35214367
NESTED_INNER_APP = 1390675395
NESTED_INNER_ID = "QLYC4KMQW5RZRA7W5GYCJ4CUVWWSZKMK2V4X3XFQYSGYCJH6LI4Q/inner/5"


@pytest.fixture()
def algorand_mainnet() -> AlgorandClient:
    return AlgorandClient.main_net()


def test_nested_inners_from_indexer(algorand_mainnet: AlgorandClient) -> None:
    txns = get_subscribed_transactions_for_test(
        sub_info={
            "filters": [
                {
                    "name": "default",
                    "filter": {
                        "app_id": NESTED_INNER_APP,
                        "sender": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                    },
                }
            ],
            "max_rounds_to_sync": 1,
            "current_round": NESTED_INNER_ROUND + 1,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": NESTED_INNER_ROUND - 1,
        },
        algorand=algorand_mainnet,
    )

    assert len(txns["subscribed_transactions"]) == 1
    assert txns["subscribed_transactions"][0]["id"] == NESTED_INNER_ID

    txn = txns["subscribed_transactions"][0]
    assert txn == {
        "application-transaction": {
            "accounts": [],
            "application-args": [
                "AA==",
                "Aw==",
                "AAAAAAAAAAA=",
                "BAAAAAAABgTFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            ],
            "application-id": 1390675395,
            "foreign-apps": [],
            "foreign-assets": [
                1390638935,
            ],
            "global-state-schema": {
                "num-byte-slice": 0,
                "num-uint": 0,
            },
            "local-state-schema": {
                "num-byte-slice": 0,
                "num-uint": 0,
            },
            "on-completion": "noop",
        },
        "arc28_events": None,
        "balance_changes": [
            {
                "address": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                "amount": -2000,
                "asset_id": 0,
                "roles": [
                    BalanceChangeRole.Sender,
                ],
            },
        ],
        "close-rewards": 0,
        "closing-amount": 0,
        "confirmed-round": 35214367,
        "fee": 2000,
        "filters_matched": None,
        "first-valid": 35214365,
        "global-state-delta": [
            {
                "key": "",
                "value": {
                    "action": 1,
                    "bytes": "AAAAAAAAAAQAAAAAAhlUHw==",
                    "uint": 0,
                },
            },
            {
                "key": "AA==",
                "value": {
                    "action": 1,
                    "bytes": "YC4Bj8ZCXdiWg6+eYEL5yV0gvi3ucnEckrGx2BQXDDIAAAAAUuN3VwAAAAAOsZeDAQAAAABS43dXAAAAAFLkB4YAAAAAAAAAAAAAAAAAAAAA/////5S/nq4AAAAAa0BhUQAAAA91+xl0AAAAAALtZZ8AAAAAAwsGTgAAAAAAAA==",
                    "uint": 0,
                },
            },
            {
                "key": "AQ==",
                "value": {
                    "action": 1,
                    "bytes": "h2MAAAAAAAAABQAAAAAAAAAZAAAAAAAAAB6KqC3yOXMVr2XD4nTi43RC3Rv0AGIvri+ssClC+HVNQgAAAAAAAAAAAA==",
                    "uint": 0,
                },
            },
        ],
        "group": "6ZssGapPFZ+DyccRludq0YjZigi05/FSeUAOFNDGGlo=",
        "id": "QLYC4KMQW5RZRA7W5GYCJ4CUVWWSZKMK2V4X3XFQYSGYCJH6LI4Q/inner/5",
        "inner-txns": [
            {
                "arc28_events": None,
                "asset-transfer-transaction": {
                    "amount": 536012365,
                    "asset-id": 1390638935,
                    "close-amount": 0,
                    "receiver": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                },
                "balance_changes": [
                    {
                        "address": "RS7QNBEPRRIBGI5COVRWFCRUS5NC5NX7UABZSTSFXQ6F74EP3CNLT4CNAM",
                        "amount": -536012365,
                        "asset_id": 1390638935,
                        "roles": [
                            BalanceChangeRole.Sender,
                        ],
                    },
                    {
                        "address": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                        "amount": 536012365,
                        "asset_id": 1390638935,
                        "roles": [
                            BalanceChangeRole.Receiver,
                        ],
                    },
                ],
                "close-rewards": 0,
                "closing-amount": 0,
                "confirmed-round": 35214367,
                "fee": 0,
                "filters_matched": None,
                "first-valid": 35214365,
                "inner-txns": None,
                "intra-round-offset": 142,
                "last-valid": 35214369,
                "receiver-rewards": 0,
                "round-time": 1705252440,
                "sender": "RS7QNBEPRRIBGI5COVRWFCRUS5NC5NX7UABZSTSFXQ6F74EP3CNLT4CNAM",
                "sender-rewards": 0,
                "tx-type": "axfer",
            },
        ],
        "intra-round-offset": 147,
        "last-valid": 35214369,
        "logs": [
            "R2hHHwQAAAAAAAYExQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==",
            "AAAAAAAAYaAAAAAAH/LmTQAAAAAAAAAA",
            "PNZU+gAEIaZlfCPaQTne/tLHvhC5yf/+JYJqpN1uNQLOFg2mAAAAAAAAAAAAAAAAAAYExQAAAAAf8uZNAAAAAAAAAAAAAAAPdfsZdAAAAAAC7WWf",
        ],
        "parent_transaction_id": "QLYC4KMQW5RZRA7W5GYCJ4CUVWWSZKMK2V4X3XFQYSGYCJH6LI4Q",
        "receiver-rewards": 0,
        "round-time": 1705252440,
        "sender": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
        "sender-rewards": 0,
        "tx-type": "appl",
    }


def test_nested_inners_from_algod(algorand_mainnet: AlgorandClient) -> None:
    txns = get_subscribed_transactions_for_test(
        sub_info={
            "filters": [
                {
                    "name": "default",
                    "filter": {
                        "app_id": NESTED_INNER_APP,
                        "sender": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                    },
                }
            ],
            "max_rounds_to_sync": 1,
            "current_round": NESTED_INNER_ROUND + 1,
            "sync_behaviour": "sync-oldest",
            "watermark": NESTED_INNER_ROUND - 1,
        },
        algorand=algorand_mainnet,
    )

    assert len(txns["subscribed_transactions"]) == 1
    assert txns["subscribed_transactions"][0]["id"] == NESTED_INNER_ID

    txn = txns["subscribed_transactions"][0]
    assert remove_none_values(txn) == {
        "application-transaction": {
            "application-args": [
                "AA==",
                "Aw==",
                "AAAAAAAAAAA=",
                "BAAAAAAABgTFAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            ],
            "application-id": 1390675395,
            "approval-program": "",
            "clear-state-program": "",
            "foreign-assets": [
                1390638935,
            ],
            "on-completion": "noop",
        },
        "balance_changes": [
            {
                "address": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                "amount": -2000,
                "asset_id": 0,
                "roles": [
                    BalanceChangeRole.Sender,
                ],
            },
        ],
        "confirmed-round": 35214367,
        "fee": 2000,
        "filters_matched": [
            "default",
        ],
        "first-valid": 35214365,
        "genesis-hash": "wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=",
        "group": "6ZssGapPFZ+DyccRludq0YjZigi05/FSeUAOFNDGGlo=",
        "id": "QLYC4KMQW5RZRA7W5GYCJ4CUVWWSZKMK2V4X3XFQYSGYCJH6LI4Q/inner/5",
        "inner-txns": [
            {
                "asset-transfer-transaction": {
                    "amount": 536012365,
                    "asset-id": 1390638935,
                    "receiver": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                },
                "balance_changes": [
                    {
                        "address": "RS7QNBEPRRIBGI5COVRWFCRUS5NC5NX7UABZSTSFXQ6F74EP3CNLT4CNAM",
                        "amount": -536012365,
                        "asset_id": 1390638935,
                        "roles": [
                            BalanceChangeRole.Sender,
                        ],
                    },
                    {
                        "address": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
                        "amount": 536012365,
                        "asset_id": 1390638935,
                        "roles": [
                            BalanceChangeRole.Receiver,
                        ],
                    },
                ],
                "confirmed-round": 35214367,
                "fee": 0,
                "first-valid": 35214365,
                "genesis-hash": "wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=",
                "id": "QLYC4KMQW5RZRA7W5GYCJ4CUVWWSZKMK2V4X3XFQYSGYCJH6LI4Q/inner/5",
                "intra-round-offset": 148,
                "last-valid": 35214369,
                "lease": "",
                "note": "",
                "parent_transaction_id": "QLYC4KMQW5RZRA7W5GYCJ4CUVWWSZKMK2V4X3XFQYSGYCJH6LI4Q",
                "round-time": 1705252440,
                "sender": "RS7QNBEPRRIBGI5COVRWFCRUS5NC5NX7UABZSTSFXQ6F74EP3CNLT4CNAM",
                "tx-type": "axfer",
            },
        ],
        "intra-round-offset": 147,
        "last-valid": 35214369,
        "lease": "",
        "logs": [
            "R2hHHwQAAAAAAAYExQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==",
            "AAAAAAAAYaAAAAAAH/LmTQAAAAAAAAAA",
            "PNZU+gAEIaZlfCPaQTne/tLHvhC5yf/+JYJqpN1uNQLOFg2mAAAAAAAAAAAAAAAAAAYExQAAAAAf8uZNAAAAAAAAAAAAAAAPdfsZdAAAAAAC7WWf",
        ],
        "note": "",
        "parent_transaction_id": "QLYC4KMQW5RZRA7W5GYCJ4CUVWWSZKMK2V4X3XFQYSGYCJH6LI4Q",
        "round-time": 1705252440,
        "sender": "AACCDJTFPQR5UQJZ337NFR56CC44T776EWBGVJG5NY2QFTQWBWTALTEN4A",
        "tx-type": "appl",
    }
