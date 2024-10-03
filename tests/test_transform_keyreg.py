import pytest
from algokit_subscriber.types.subscription import BalanceChangeRole
from algokit_subscriber.types.transaction import TransactionType
from algokit_utils.beta.algorand_client import AlgorandClient

from .transactions import get_subscribed_transactions_for_test, remove_none_values

KEYREG_ROUND = 34418662
KEYREG_TXN_ID = "LSTIW7IBLO4SFPLFAI45WAV3NPXYPX6RWPTZ5KYDL3NX2LTJFXNA"


@pytest.fixture()
def algorand_mainnet() -> AlgorandClient:
    return AlgorandClient.main_net()


def test_keyreg_from_indexer(algorand_mainnet: AlgorandClient) -> None:
    txns = get_subscribed_transactions_for_test(
        sub_info={
            "filters": [
                {
                    "name": "default",
                    "filter": {
                        "type": TransactionType.keyreg.value,
                        "sender": "HQQRVWPYAHABKCXNMZRG242Z5GWFTJMRO63HDCLF23ZWCT3IPQXIGQ2KGY",
                    },
                }
            ],
            "max_rounds_to_sync": 1,
            "current_round": KEYREG_ROUND + 1,
            "sync_behaviour": "catchup-with-indexer",
            "watermark": KEYREG_ROUND - 1,
        },
        algorand=algorand_mainnet,
    )

    assert len(txns["subscribed_transactions"]) == 1
    txn = txns["subscribed_transactions"][0]
    # https://allo.info/tx/LSTIW7IBLO4SFPLFAI45WAV3NPXYPX6RWPTZ5KYDL3NX2LTJFXNA
    assert txn["id"] == KEYREG_TXN_ID

    assert txn == {
        "arc28_events": None,
        "balance_changes": [
            {
                "address": "HQQRVWPYAHABKCXNMZRG242Z5GWFTJMRO63HDCLF23ZWCT3IPQXIGQ2KGY",
                "amount": -1000,
                "asset_id": 0,
                "roles": [
                    BalanceChangeRole.Sender,
                ],
            },
        ],
        "close-rewards": 0,
        "closing-amount": 0,
        "confirmed-round": 34418662,
        "fee": 1000,
        "filters_matched": [
            "default",
        ],
        "first-valid": 34418595,
        "genesis-hash": "wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=",
        "genesis-id": "mainnet-v1.0",
        "id": "LSTIW7IBLO4SFPLFAI45WAV3NPXYPX6RWPTZ5KYDL3NX2LTJFXNA",
        "inner-txns": None,
        "intra-round-offset": 54,
        "keyreg-transaction": {
            "non-participation": False,
            "selection-participation-key": "Fsp1QLE/fXpmq5fsk/bWP8P1+H8n30bMD3X7hPdk/GU=",
            "state-proof-key": "Qld9eu3U/OhHohBMF4atWbKbDQB5NGO2vPl5sZ9q9yHssmrbnQIOlhujP3vaSdFXqstnzD77Z85yrlfxJFfu+g==",
            "vote-first-valid": 34300000,
            "vote-key-dilution": 2450,
            "vote-last-valid": 40300000,
            "vote-participation-key": "yUR+nfHtSb2twOaprEXrnYjkhbFMBtmXW9D8x+/ROBg=",
        },
        "last-valid": 34419595,
        "receiver-rewards": 0,
        "round-time": 1702579204,
        "sender": "HQQRVWPYAHABKCXNMZRG242Z5GWFTJMRO63HDCLF23ZWCT3IPQXIGQ2KGY",
        "sender-rewards": 0,
        "signature": {
            "sig": "zs+8H5J4hXmmKk36uEupgupE5Filw/xMae0ox5c7yuHM4jYVPLPBYHLOdPapguScPzuz0Lney/+V9MFrKLj9Dw==",
        },
        "tx-type": "keyreg",
    }


def test_keyreg_from_algod(algorand_mainnet: AlgorandClient) -> None:
    txns = get_subscribed_transactions_for_test(
        sub_info={
            "filters": [
                {
                    "name": "default",
                    "filter": {
                        "type": TransactionType.keyreg.value,
                        "sender": "HQQRVWPYAHABKCXNMZRG242Z5GWFTJMRO63HDCLF23ZWCT3IPQXIGQ2KGY",
                    },
                }
            ],
            "max_rounds_to_sync": 1,
            "current_round": KEYREG_ROUND,
            "sync_behaviour": "sync-oldest",
            "watermark": KEYREG_ROUND - 1,
        },
        algorand=algorand_mainnet,
    )

    assert len(txns["subscribed_transactions"]) == 1
    txn = txns["subscribed_transactions"][0]
    # https://allo.info/tx/LSTIW7IBLO4SFPLFAI45WAV3NPXYPX6RWPTZ5KYDL3NX2LTJFXNA
    assert txn["id"] == KEYREG_TXN_ID
    assert remove_none_values(txn) == {
        "balance_changes": [
            {
                "address": "HQQRVWPYAHABKCXNMZRG242Z5GWFTJMRO63HDCLF23ZWCT3IPQXIGQ2KGY",
                "amount": -1000,
                "asset_id": 0,
                "roles": [
                    BalanceChangeRole.Sender,
                ],
            },
        ],
        "confirmed-round": 34418662,
        "fee": 1000,
        "filters_matched": [
            "default",
        ],
        "first-valid": 34418595,
        "genesis-hash": "wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=",
        "genesis-id": "mainnet-v1.0",
        "id": "LSTIW7IBLO4SFPLFAI45WAV3NPXYPX6RWPTZ5KYDL3NX2LTJFXNA",
        "intra-round-offset": 54,
        "keyreg-transaction": {
            "non-participation": False,
            "selection-participation-key": "Fsp1QLE/fXpmq5fsk/bWP8P1+H8n30bMD3X7hPdk/GU=",
            "state-proof-key": "Qld9eu3U/OhHohBMF4atWbKbDQB5NGO2vPl5sZ9q9yHssmrbnQIOlhujP3vaSdFXqstnzD77Z85yrlfxJFfu+g==",
            "vote-first-valid": 34300000,
            "vote-key-dilution": 2450,
            "vote-last-valid": 40300000,
            "vote-participation-key": "yUR+nfHtSb2twOaprEXrnYjkhbFMBtmXW9D8x+/ROBg=",
        },
        "last-valid": 34419595,
        "lease": "",
        "note": "",
        "round-time": 1702579204,
        "sender": "HQQRVWPYAHABKCXNMZRG242Z5GWFTJMRO63HDCLF23ZWCT3IPQXIGQ2KGY",
        # TODO: Investigate why signature is in the snapshot
        # "signature": {
        #   "sig": "zs+8H5J4hXmmKk36uEupgupE5Filw/xMae0ox5c7yuHM4jYVPLPBYHLOdPapguScPzuz0Lney/+V9MFrKLj9Dw==",
        # },
        "tx-type": "keyreg",
    }
