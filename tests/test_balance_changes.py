from typing import TYPE_CHECKING

from algokit_subscriber.types.subscription import BalanceChangeRole
from algokit_utils.beta.composer import (
    AssetCreateParams,
    AssetDestroyParams,
    AssetOptInParams,
    AssetTransferParams,
    PayParams,
)

if TYPE_CHECKING:
    from algokit_utils.beta.algorand_client import AlgorandClient

from .accounts import generate_account
from .filter_fixture import filter_fixture  # noqa: F401
from .transactions import get_confirmations


def test_asset_create_txns(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]

    sender = generate_account(localnet)
    txns = (
        localnet.new_group()
        .add_asset_create(
            AssetCreateParams(sender=sender, static_fee=2000, total=100_000_000)
        )
        .execute()
    )
    confirmations = get_confirmations(localnet, txns.tx_ids)
    asset = confirmations[0]["asset-index"]

    subscription = filter_fixture["subscribe_and_verify"](
        {
            "balance_changes": [{"role": [BalanceChangeRole.AssetCreator]}],
        },
        txns.tx_ids[0],
    )

    transaction = subscription["subscribed_transactions"][0]
    assert transaction["balance_changes"]
    assert len(transaction["balance_changes"]) == 2

    assert transaction["balance_changes"][0]["address"] == sender
    assert transaction["balance_changes"][0]["amount"] == -2000
    assert transaction["balance_changes"][0]["roles"] == [BalanceChangeRole.Sender]
    assert transaction["balance_changes"][0]["asset_id"] == 0

    assert transaction["balance_changes"][1]["address"] == sender
    assert transaction["balance_changes"][1]["amount"] == 100_000_000
    assert transaction["balance_changes"][1]["roles"] == [
        BalanceChangeRole.AssetCreator
    ]
    assert transaction["balance_changes"][1]["asset_id"] == asset


def test_asset_destroy_txns(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]

    sender = generate_account(localnet)
    create_asset_txns = (
        localnet.new_group()
        .add_asset_create(
            AssetCreateParams(
                sender=sender, static_fee=2000, total=100_000_000, manager=sender
            )
        )
        .execute()
    )
    asset = get_confirmations(localnet, create_asset_txns.tx_ids)[0]["asset-index"]

    txns = (
        localnet.new_group()
        .add_asset_destroy(
            AssetDestroyParams(sender=sender, static_fee=2000, asset_id=asset)
        )
        .execute()
    )

    subscription = filter_fixture["subscribe_and_verify"](
        {
            "balance_changes": [{"role": [BalanceChangeRole.AssetDestroyer]}],
        },
        txns.tx_ids[0],
    )

    transaction = subscription["subscribed_transactions"][0]
    assert transaction["balance_changes"]
    assert len(transaction["balance_changes"]) == 2

    assert transaction["balance_changes"][0]["address"] == sender
    assert transaction["balance_changes"][0]["amount"] == -2000
    assert transaction["balance_changes"][0]["roles"] == [BalanceChangeRole.Sender]
    assert transaction["balance_changes"][0]["asset_id"] == 0

    assert transaction["balance_changes"][1]["address"] == sender
    assert transaction["balance_changes"][1]["amount"] == 0
    assert transaction["balance_changes"][1]["roles"] == [
        BalanceChangeRole.AssetDestroyer
    ]
    assert transaction["balance_changes"][1]["asset_id"] == asset


def test_balance_change_filter_on_fee(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]

    random_account = generate_account(localnet, amount=1_000_000)
    test_account = generate_account(localnet)

    txns = (
        localnet.new_group()
        .add_asset_create(
            AssetCreateParams(sender=random_account, static_fee=3000, total=1)
        )
        .add_asset_create(
            AssetCreateParams(sender=test_account, static_fee=1000, total=1)
        )
        .add_asset_create(
            AssetCreateParams(sender=test_account, static_fee=3000, total=1)
        )
        .add_asset_create(
            AssetCreateParams(sender=test_account, static_fee=5000, total=1)
        )
        .execute()
    )

    filter_fixture["subscribe_and_verify_filter"](
        {
            "balance_changes": [
                {
                    "asset_id": [0],
                    "address": test_account,
                    "role": [BalanceChangeRole.Sender],
                    "min_amount": -4000,
                    "max_amount": -2000,
                    "min_absolute_amount": 2000,
                    "max_absolute_amount": 4000,
                }
            ],
        },
        [txns.tx_ids[2]],
    )


def test_various_filters_on_payments(filter_fixture: dict) -> None:
    localnet: AlgorandClient = filter_fixture["localnet"]
    subscribe_and_verify_filter = filter_fixture["subscribe_and_verify_filter"]

    account = generate_account(localnet, 200_000)
    account2 = generate_account(localnet, 200_000)
    account3 = generate_account(localnet, 200_000)

    txns = (
        localnet.new_group()
        .add_payment(
            PayParams(amount=1000, sender=account, receiver=account2, static_fee=1000)
        )
        .add_payment(
            PayParams(amount=1000, sender=account2, receiver=account, static_fee=1000)
        )
        .add_payment(
            PayParams(amount=2000, sender=account, receiver=account2, static_fee=1000)
        )
        .add_payment(
            PayParams(amount=2000, sender=account2, receiver=account, static_fee=1000)
        )
        .add_payment(
            PayParams(amount=3000, sender=account, receiver=account2, static_fee=1000)
        )
        .add_payment(
            PayParams(amount=3000, sender=account2, receiver=account, static_fee=1000)
        )
        .add_payment(
            PayParams(
                amount=100_000,
                sender=account,
                receiver=account2,
                static_fee=1000,
                close_remainder_to=account3,
            )
        )
        .add_payment(
            PayParams(
                amount=100_000,
                sender=account2,
                receiver=account,
                static_fee=1000,
                close_remainder_to=account,
            )
        )
        .add_payment(
            PayParams(
                amount=100_000,
                sender=account3,
                receiver=account2,
                static_fee=2000,
                close_remainder_to=account,
            )
        )
        .add_payment(
            PayParams(amount=0, sender=account, receiver=account, static_fee=0)
        )
        .execute()
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [0],
                    "address": account,
                    "role": [BalanceChangeRole.Sender],
                    "min_absolute_amount": 2001,
                    "max_absolute_amount": 3000,
                }
            ],
        },
        txns.tx_ids[2],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [0],
                    "address": account,
                    "role": [BalanceChangeRole.Sender],
                    "min_amount": -3000,
                    "max_amount": -2001,
                }
            ],
        },
        txns.tx_ids[2],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [0],
                    "address": account,
                    "min_amount": -2000,
                    "max_amount": -2000,
                }
            ],
        },
        txns.tx_ids[0],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [0],
                    "address": account,
                    "min_amount": 1000,
                    "max_amount": 1000,
                }
            ],
        },
        txns.tx_ids[1],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [0],
                    "address": account2,
                    "role": [BalanceChangeRole.Sender],
                    "min_amount": -3000,
                    "max_amount": -2001,
                    "min_absolute_amount": 2001,
                    "max_absolute_amount": 3000,
                }
            ],
        },
        txns.tx_ids[3],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [0],
                    "address": account,
                    "min_absolute_amount": 1,
                    "max_absolute_amount": 1000,
                }
            ],
        },
        txns.tx_ids[1],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [0],
                    "address": account2,
                    "max_absolute_amount": 1000,
                }
            ],
        },
        txns.tx_ids[0],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [0],
                    "address": account3,
                    "role": BalanceChangeRole.CloseTo,
                }
            ],
        },
        txns.tx_ids[6],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [0],
                    "address": account3,
                    "role": [BalanceChangeRole.CloseTo, BalanceChangeRole.Sender],
                    "min_amount": 0,
                }
            ],
        },
        txns.tx_ids[6],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "min_amount": 196_000,
                }
            ],
        },
        txns.tx_ids[7],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "address": [account2, account3],
                    "min_absolute_amount": 296_000,
                    "max_absolute_amount": 296_000,
                }
            ],
        },
        txns.tx_ids[8],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "min_absolute_amount": 297_000,
                }
            ],
        },
        txns.tx_ids[7],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "max_amount": -297_000,
                }
            ],
        },
        txns.tx_ids[7],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "min_amount": 0,
                    "max_amount": 0,
                }
            ],
        },
        txns.tx_ids[9],
    )

    address = {
        account: "account1",
        account2: "account2",
        account3: "account3",
    }

    result = filter_fixture["subscribe_algod"](
        {"balance_changes": [{"min_amount": 0}]},
        localnet.client.algod.pending_transaction_info(txns.tx_ids[0])[
            "confirmed-round"
        ],
    )

    balance_changes = [
        [
            f"{address[b['address']]}: {b['amount']} ({', '.join([r.value for r in b['roles']])})"
            for b in sorted(s["balance_changes"], key=lambda x: address[x["address"]])
        ]
        for s in result["subscribed_transactions"]
    ]

    expected_balance_changes = [
        [
            "account1: -2000 (Sender)",
            "account2: 1000 (Receiver)",
        ],
        [
            "account1: 1000 (Receiver)",
            "account2: -2000 (Sender)",
        ],
        [
            "account1: -3000 (Sender)",
            "account2: 2000 (Receiver)",
        ],
        [
            "account1: 2000 (Receiver)",
            "account2: -3000 (Sender)",
        ],
        [
            "account1: -4000 (Sender)",
            "account2: 3000 (Receiver)",
        ],
        [
            "account1: 3000 (Receiver)",
            "account2: -4000 (Sender)",
        ],
        [
            "account1: -197000 (Sender)",
            "account2: 100000 (Receiver)",
            "account3: 96000 (CloseTo)",
        ],
        [
            "account1: 296000 (Receiver, CloseTo)",
            "account2: -297000 (Sender)",
        ],
        [
            "account1: 194000 (CloseTo)",
            "account2: 100000 (Receiver)",
            "account3: -296000 (Sender)",
        ],
        [
            "account1: 0 (Sender, Receiver)",
        ],
    ]

    assert balance_changes == expected_balance_changes


def test_various_filters_on_axfers(filter_fixture: dict) -> None:  # noqa: PLR0915
    localnet: AlgorandClient = filter_fixture["localnet"]
    subscribe_and_verify_filter = filter_fixture["subscribe_and_verify_filter"]

    test_account = generate_account(localnet)
    account = generate_account(localnet, 1_000_000)
    account2 = generate_account(localnet, 1_000_000)
    account3 = generate_account(localnet, 1_000_000)

    asset1 = localnet.send.asset_create(
        AssetCreateParams(sender=test_account, total=1000, clawback=test_account)
    )["confirmation"]["asset-index"]
    asset2 = localnet.send.asset_create(
        AssetCreateParams(sender=test_account, total=1001, clawback=test_account)
    )["confirmation"]["asset-index"]

    localnet.send.asset_opt_in(AssetOptInParams(sender=account, asset_id=asset1))
    localnet.send.asset_opt_in(AssetOptInParams(sender=account2, asset_id=asset1))
    localnet.send.asset_opt_in(AssetOptInParams(sender=account3, asset_id=asset1))
    localnet.send.asset_opt_in(AssetOptInParams(sender=account, asset_id=asset2))
    localnet.send.asset_opt_in(AssetOptInParams(sender=account2, asset_id=asset2))
    localnet.send.asset_opt_in(AssetOptInParams(sender=account3, asset_id=asset2))

    localnet.send.asset_transfer(
        AssetTransferParams(
            sender=test_account, receiver=account, asset_id=asset1, amount=10
        )
    )
    localnet.send.asset_transfer(
        AssetTransferParams(
            sender=test_account, receiver=account2, asset_id=asset1, amount=10
        )
    )
    localnet.send.asset_transfer(
        AssetTransferParams(
            sender=test_account, receiver=account3, asset_id=asset1, amount=20
        )
    )
    localnet.send.asset_transfer(
        AssetTransferParams(
            sender=test_account, receiver=account, asset_id=asset2, amount=10
        )
    )
    localnet.send.asset_transfer(
        AssetTransferParams(
            sender=test_account, receiver=account2, asset_id=asset2, amount=23
        )
    )

    txns = (
        localnet.new_group()
        .add_asset_transfer(
            AssetTransferParams(
                sender=account, receiver=account2, asset_id=asset1, amount=1
            )
        )
        .add_asset_transfer(
            AssetTransferParams(
                sender=account2, receiver=account, asset_id=asset1, amount=1
            )
        )
        .add_asset_transfer(
            AssetTransferParams(
                sender=account, receiver=account2, asset_id=asset1, amount=2
            )
        )
        .add_asset_transfer(
            AssetTransferParams(
                sender=account2, receiver=account, asset_id=asset1, amount=2
            )
        )
        .add_asset_transfer(
            AssetTransferParams(
                sender=test_account,
                receiver=account2,
                asset_id=asset1,
                amount=3,
                clawback_target=account,
            )
        )
        .add_asset_transfer(
            AssetTransferParams(
                sender=test_account,
                receiver=account,
                asset_id=asset1,
                amount=3,
                clawback_target=account2,
            )
        )
        .add_asset_transfer(
            AssetTransferParams(
                sender=account,
                receiver=account2,
                asset_id=asset1,
                amount=7,
                close_asset_to=account3,
            )
        )
        .add_asset_opt_in(AssetOptInParams(sender=account, asset_id=asset1))
        .add_asset_transfer(
            AssetTransferParams(
                sender=account2,
                receiver=account,
                asset_id=asset1,
                amount=7,
                close_asset_to=account,
            )
        )
        .add_asset_opt_in(AssetOptInParams(sender=account2, asset_id=asset1))
        .add_asset_transfer(
            AssetTransferParams(
                sender=account3,
                receiver=account2,
                asset_id=asset1,
                amount=3,
                close_asset_to=account,
            )
        )
        .add_asset_transfer(
            AssetTransferParams(
                sender=account, receiver=account2, asset_id=asset2, amount=1
            )
        )
        .add_asset_transfer(
            AssetTransferParams(
                sender=account2, receiver=account, asset_id=asset2, amount=23
            )
        )
        .execute()
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [asset1],
                    "address": account,
                    "role": [BalanceChangeRole.Sender],
                    "min_absolute_amount": 1.1,
                    "max_absolute_amount": 2,
                }
            ],
        },
        txns.tx_ids[2],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [asset1],
                    "address": account,
                    "role": [BalanceChangeRole.Sender],
                    "min_amount": -2,
                    "max_amount": -1.1,
                }
            ],
        },
        txns.tx_ids[2],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [asset1],
                    "address": account,
                    "min_amount": -1,
                    "max_amount": -1,
                }
            ],
        },
        txns.tx_ids[0],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [asset1],
                    "address": account,
                    "min_amount": 1,
                    "max_amount": 1,
                }
            ],
        },
        txns.tx_ids[1],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [asset1],
                    "address": account2,
                    "role": [BalanceChangeRole.Sender],
                    "min_amount": -2,
                    "max_amount": -1.1,
                    "min_absolute_amount": 1.1,
                    "max_absolute_amount": 2,
                }
            ],
        },
        txns.tx_ids[3],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [asset1],
                    "address": account,
                    "min_amount": 0.1,
                    "max_absolute_amount": 1,
                }
            ],
        },
        txns.tx_ids[1],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [asset1],
                    "address": account2,
                    "min_amount": 0.1,
                    "max_absolute_amount": 1,
                }
            ],
        },
        txns.tx_ids[0],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [asset1],
                    "address": account3,
                    "role": BalanceChangeRole.CloseTo,
                }
            ],
        },
        txns.tx_ids[6],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [asset1],
                    "address": account3,
                    "role": [BalanceChangeRole.CloseTo, BalanceChangeRole.Sender],
                    "min_amount": 0,
                }
            ],
        },
        txns.tx_ids[6],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [asset1],
                    "min_amount": 18,
                }
            ],
        },
        txns.tx_ids[10],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "address": [account2, account3],
                    "min_absolute_amount": 17,
                    "max_absolute_amount": 17,
                }
            ],
        },
        txns.tx_ids[8],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "asset_id": [asset1],
                    "min_absolute_amount": 23,
                }
            ],
        },
        txns.tx_ids[10],
    )

    subscribe_and_verify_filter(
        {
            "balance_changes": [
                {
                    "address": account2,
                    "max_amount": -23,
                    "max_absolute_amount": 23,  # Stop algo balance changes triggering it
                }
            ],
        },
        txns.tx_ids[12],
    )

    address = {}
    address[account] = "account1"
    address[account2] = "account2"
    address[account3] = "account3"
    address[test_account] = "testAccount"

    result = filter_fixture["subscribe_algod"](
        {"balance_changes": [{"min_amount": 0}]},
        localnet.client.algod.pending_transaction_info(txns.tx_ids[0])[
            "confirmed-round"
        ],
    )

    assets = {}
    assets[asset1] = "asset1"
    assets[asset2] = "asset2"

    balance_changes = []
    for s in result["subscribed_transactions"]:
        transaction_changes = []
        for b in s["balance_changes"]:
            if b["asset_id"] != 0:
                roles = ", ".join([role.value for role in b["roles"]])
                asset_id = assets[b["asset_id"]]
                change_str = (
                    f"{address[b['address']]}: {b['amount']} x {asset_id} ({roles})"
                )
                transaction_changes.append(change_str)
        balance_changes.append(sorted(transaction_changes))

    expected_balance_changes = [
        [
            "account1: -1 x asset1 (Sender)",
            "account2: 1 x asset1 (Receiver)",
        ],
        [
            "account1: 1 x asset1 (Receiver)",
            "account2: -1 x asset1 (Sender)",
        ],
        [
            "account1: -2 x asset1 (Sender)",
            "account2: 2 x asset1 (Receiver)",
        ],
        [
            "account1: 2 x asset1 (Receiver)",
            "account2: -2 x asset1 (Sender)",
        ],
        [
            "account1: -3 x asset1 (Sender)",
            "account2: 3 x asset1 (Receiver)",
        ],
        [
            "account1: 3 x asset1 (Receiver)",
            "account2: -3 x asset1 (Sender)",
        ],
        [
            "account1: -10 x asset1 (Sender)",
            "account2: 7 x asset1 (Receiver)",
            "account3: 3 x asset1 (CloseTo)",
        ],
        [
            "account1: 0 x asset1 (Sender, Receiver)",
        ],
        [
            "account1: 17 x asset1 (Receiver, CloseTo)",
            "account2: -17 x asset1 (Sender)",
        ],
        [
            "account2: 0 x asset1 (Sender, Receiver)",
        ],
        [
            "account1: 20 x asset1 (CloseTo)",
            "account2: 3 x asset1 (Receiver)",
            "account3: -23 x asset1 (Sender)",
        ],
        [
            "account1: -1 x asset2 (Sender)",
            "account2: 1 x asset2 (Receiver)",
        ],
        [
            "account1: 23 x asset2 (Receiver)",
            "account2: -23 x asset2 (Sender)",
        ],
    ]

    for i, bc in enumerate(balance_changes):
        assert bc == expected_balance_changes[i]
