import base64
import hashlib
import time
from collections.abc import Callable
from typing import Any, cast

import algosdk
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient

from .block import get_blocks_bulk
from .indexer_lookup import search_transactions
from .transform import (
    algod_on_complete_to_indexer_on_complete,
    block_data_to_block_metadata,
    extract_balance_changes_from_block_transaction,
    get_block_transactions,
    get_indexer_transaction_from_algod_transaction,
)
from .types.arc28 import Arc28EventGroup, Arc28EventToProcess, EmittedArc28Event
from .types.block import TransactionInBlock
from .types.indexer import TransactionResult
from .types.subscription import (
    BalanceChange,
    BalanceChangeRole,
    BlockMetadata,
    NamedTransactionFilter,
    SubscribedTransaction,
    TransactionFilter,
    TransactionSubscriptionParams,
    TransactionSubscriptionResult,
)
from .types.transaction import TransactionType
from .utils import chunk_array, encode_address, logger

SearchForTransactions = dict[str, Any]


def deduplicate_subscribed_transactions(
    txns: list[SubscribedTransaction],
) -> list[SubscribedTransaction]:
    """
    Deduplicate subscribed transactions based on their ID.

    :param txns: List of subscribed transactions
    :return: Deduplicated list of subscribed transactions
    """
    result_dict: dict[str, SubscribedTransaction] = {}

    for txn in txns:
        if txn["id"] in result_dict:
            result_dict[txn["id"]]["filters_matched"].extend(txn["filters_matched"])
        else:
            result_dict[txn["id"]] = txn.copy()

    return list(result_dict.values())


def transaction_is_in_arc28_event_group(
    group: Arc28EventGroup, app_id: int, transaction: Callable[[], TransactionResult]
) -> bool:
    """
    Check if a transaction is in an ARC-28 event group.

    :param group: The ARC-28 event group to check against
    :param app_id: The application ID of the transaction
    :param transaction: A function that returns the transaction result
    :return: True if the transaction is in the ARC-28 event group, False otherwise
    """
    in_group = (
        not group.get("process_for_app_ids") or app_id in group["process_for_app_ids"]
    )

    if in_group and group.get("process_transaction") is not None:
        # Lazily evaluate transaction so it's only evaluated if needed
        # since creating the transaction object may be expensive if from algod
        in_group = group["process_transaction"](transaction())

    return in_group


def has_emitted_matching_arc28_event(  # noqa: PLR0913
    logs: list[str],
    all_events: list[Arc28EventToProcess],
    event_groups: list[Arc28EventGroup],
    event_filter: list[dict[str, str]],
    app_id: int,
    transaction: Callable[[], TransactionResult],
) -> bool:
    """
    Check if a transaction has emitted a matching ARC-28 event.

    :param logs: The transaction logs encoded as bas64 strings
    :param all_events: All ARC-28 events to process
    :param event_groups: All ARC-28 event groups
    :param event_filter: The event filter to apply
    :param app_id: The application ID
    :param transaction: A function that returns the transaction result
    :return: True if a matching ARC-28 event has been emitted, False otherwise
    """
    potential_events = [
        e
        for e in all_events
        if any(
            f["event_name"] == e["event_name"] and f["group_name"] == e["group_name"]
            for f in event_filter
        )
        if transaction_is_in_arc28_event_group(
            next(g for g in event_groups if g["group_name"] == e["group_name"]),
            app_id,
            transaction,
        )
    ]

    hex_prefixes = [base64.b64decode(log).hex()[:8] for log in logs]

    # check if any of the hex_prefixes match the event_prefixes
    for hex_prefix in hex_prefixes:
        for event in potential_events:
            if hex_prefix == event["event_prefix"]:
                return True

    return False


def extract_arc28_events(
    transaction_id: str,
    logs: list[bytes],
    events: list[Arc28EventToProcess],
    continue_on_error: Callable[[str], bool],
) -> list[EmittedArc28Event]:
    """
    Extract ARC-28 events from transaction logs.

    :param transaction_id: The ID of the transaction
    :param logs: The transaction logs
    :param events: The ARC-28 events to process
    :param continue_on_error: A function that decides whether to continue on error for a given group name
    :return: A list of emitted ARC-28 events, or an empty list if no events are found
    """
    if not events:
        return []

    emitted_events: list[EmittedArc28Event] = []

    for log in logs:
        if len(log) <= 4:  # noqa: PLR2004
            continue

        prefix = base64.b16encode(log[:4]).lower().decode()

        for e in events:
            if e["event_prefix"] != prefix:
                continue

            try:
                abi_type = algosdk.abi.ABIType.from_string(
                    f"({','.join(a['type'] for a in e['event_definition']['args'])})"
                )
                value = abi_type.decode(log[4:])

                args: list[Any] = []
                args_by_name: dict[str, Any] = {}

                for i, arg in enumerate(e["event_definition"]["args"]):
                    args.append(value[i])
                    if arg["name"]:
                        args_by_name[arg["name"]] = value[i]

                emitted_events.append(
                    {
                        **e,
                        "args": args,
                        "args_by_name": args_by_name,
                    }
                )

            except Exception as error:
                if continue_on_error(e["group_name"]):
                    logger.warn(
                        f"Warning: Encountered error while processing {e['group_name']}.{e['group_name']} on transaction {transaction_id}: {error}"
                    )
                else:
                    raise

    return emitted_events if emitted_events else []


def indexer_pre_filter(
    subscription: TransactionFilter, min_round: int, max_round: int
) -> dict[str, Any]:
    """
    Create a pre-filter function for the Indexer client based on the subscription parameters.

    :param subscription: The transaction filter parameters
    :param min_round: The minimum round number to search from
    :param max_round: The maximum round number to search to
    :return: A dictionary of pre-filter arguments for the Indexer client
    """
    # NOTE: everything in this method needs to be mirrored to `indexer_pre_filter_in_memory` below
    args = dict[str, Any]()

    if subscription.get("sender") and isinstance(subscription["sender"], str):
        args["address"] = subscription["sender"]
        args["address_role"] = "sender"

    if subscription.get("receiver") and isinstance(subscription["receiver"], str):
        args["address"] = subscription["receiver"]
        args["address_role"] = "receiver"

    if subscription.get("type") and isinstance(subscription["type"], str):
        args["txn_type"] = subscription["type"]

    if subscription.get("note_prefix"):
        args["note_prefix"] = base64.b64encode(
            subscription["note_prefix"].encode()
        ).decode()

    if subscription.get("app_id") and isinstance(subscription["app_id"], int):
        args["application_id"] = int(subscription["app_id"])

    if subscription.get("asset_id") and isinstance(subscription["asset_id"], int):
        args["asset_id"] = int(subscription["asset_id"])

    # Indexer only supports min_amount and maxAmount for non-payments if an asset ID is provided so check
    # we are looking for just payments, or we have provided asset ID before adding to pre-filter
    # if they aren't added here they will be picked up in the in-memory pre-filter
    if subscription.get("min_amount") and (
        subscription["type"] == "pay" or subscription["asset_id"]
    ):
        # Indexer only supports numbers, but even though this is less precise the in-memory indexer pre-filter will remove any false positives
        args["min_amount"] = min(subscription["min_amount"] - 1, 2**53 - 1)

    if subscription.get("max_amount") and (
        subscription["type"] == "pay"
        or (subscription.get("asset_id") and (subscription.get("min_amount", 0)) > 0)
    ):
        args["max_amount"](subscription["max_amount"]) + 1

    args["min_round"] = min_round
    args["max_round"] = max_round

    return args


def indexer_pre_filter_in_memory(  # noqa: C901
    subscription: TransactionFilter,
) -> Callable[[TransactionResult], bool]:
    """
    Create an in-memory pre-filter function based on the subscription parameters.

    This is needed to overcome the problem that when indexer matches on an inner transaction,
    it doesn't return that inner transaction, it returns the parent. We need to re-run these
    filters in-memory to identify the actual transaction(s) that were matched.

    :param subscription: The transaction filter parameters
    :return: A function that applies the pre-filter to a transaction dictionary
    """

    def filter_transaction(t: TransactionResult) -> bool:  # noqa: C901, PLR0912
        result = True
        axfer = t.get("asset-transfer-transaction")
        pay = t.get("payment-transaction")
        appl = t.get("application-transaction")
        afrz = t.get("asset-freeze-transaction")
        acfg = t.get("asset-config-transaction")

        if subscription.get("sender"):
            if isinstance(subscription["sender"], str):
                result = result and t.get("sender") == subscription["sender"]
            else:
                result = result and t.get("sender") in subscription["sender"]

        if subscription.get("receiver"):
            if isinstance(subscription["receiver"], str):
                result = result and bool(
                    axfer
                    and axfer.get("receiver") == subscription["receiver"]
                    or pay
                    and pay.get("receiver") == subscription["receiver"]
                )
            else:
                result = result and bool(
                    axfer
                    and axfer.get("receiver") in subscription["receiver"]
                    or pay
                    and pay.get("receiver") in subscription["receiver"]
                )

        if subscription.get("type"):
            if isinstance(subscription["type"], str):
                result = result and t["tx-type"] == subscription["type"]
            else:
                result = result and t["tx-type"] in subscription["type"]

        if subscription.get("note_prefix"):
            result = result and t.get("note", "").startswith(
                subscription["note_prefix"]
            )

        if subscription.get("app_id"):
            if isinstance(subscription["app_id"], int):
                result = result and bool(
                    t.get("created-application-index") == int(subscription["app_id"])
                    or appl
                    and appl.get("application-id") == int(subscription["app_id"])
                )
            else:
                result = result and bool(
                    (
                        (t.get("created-application-index") or 0)
                        in map(int, subscription["app_id"])
                    )
                    or appl
                    and appl.get("application-id", 0)
                    in map(int, subscription["app_id"])
                )

        if subscription.get("asset_id"):
            if isinstance(subscription["asset_id"], int | float):
                asset_id = int(subscription["asset_id"])
                result = result and bool(
                    t.get("created-asset-index") == asset_id
                    or acfg
                    and acfg.get("asset-id") == asset_id
                    or acfg
                    and acfg.get("asset-id") == asset_id
                    or axfer
                    and axfer.get("asset-id") == asset_id
                )
            else:
                asset_ids = set(map(int, subscription["asset_id"]))
                result = result and bool(
                    t.get("created-asset-index") in asset_ids
                    or axfer
                    and axfer.get("asset-id") in asset_ids
                    or acfg
                    and acfg.get("asset-id") in asset_ids
                    or afrz
                    and afrz.get("asset-id") in asset_ids
                )

        if subscription.get("min_amount"):
            result = result and bool(
                (pay and pay.get("amount", 0) >= subscription["min_amount"])
                or (axfer and axfer.get("amount", 0) >= subscription["min_amount"])
            )

        if subscription.get("max_amount"):
            result = result and bool(
                (pay and pay.get("amount", 0) <= subscription["max_amount"])
                or (axfer and axfer.get("amount", 0) <= subscription["max_amount"])
            )

        return result

    return filter_transaction


def get_method_selector_base64(method_signature: str) -> str:
    """
    Get the base64-encoded method selector for a given method signature.

    :param method_signature: The method signature
    :return: The base64-encoded method selector
    """
    signature_hash = hashlib.new("sha512_256", method_signature.encode()).digest()
    return base64.b64encode(signature_hash[:4]).decode("utf-8")


def has_balance_change_match(
    transaction_balance_changes: list[BalanceChange],
    filtered_balance_changes: list[dict[str, Any]] | None,
) -> bool:
    """
    Check if there's a match between the actual balance changes and the filtered balance changes.

    :param transaction_balance_changes: The actual balance changes in the transaction
    :param filtered_balance_changes: The filtered balance changes to match against
    :return: True if there's a match, False otherwise
    """
    if filtered_balance_changes is None:
        filtered_balance_changes = []

    def check_single_change(actual_change: dict, change_filter: dict) -> bool:
        # Address check
        address_check = (
            not change_filter.get("address")
            or (
                isinstance(change_filter.get("address"), list)
                and len(change_filter["address"]) == 0
            )
            or (
                actual_change.get("address")
                in (
                    change_filter["address"]
                    if isinstance(change_filter.get("address"), list)
                    else [change_filter.get("address")]
                )
            )
        )

        # Minimum absolute amount check
        min_abs_amount_check = (
            change_filter.get("min_absolute_amount") is None
            or abs(actual_change.get("amount", 0))
            >= change_filter["min_absolute_amount"]
        )

        # Maximum absolute amount check
        max_abs_amount_check = (
            change_filter.get("max_absolute_amount") is None
            or abs(actual_change.get("amount", 0))
            <= change_filter["max_absolute_amount"]
        )

        # Minimum amount check
        min_amount_check = (
            change_filter.get("min_amount") is None
            or actual_change.get("amount", 0) >= change_filter["min_amount"]
        )

        # Maximum amount check
        max_amount_check = (
            change_filter.get("max_amount") is None
            or actual_change.get("amount", 0) <= change_filter["max_amount"]
        )

        # Asset ID check
        asset_id_check = (
            change_filter.get("asset_id") is None
            or (
                isinstance(change_filter.get("asset_id"), list)
                and len(change_filter["asset_id"]) == 0
            )
            or (
                actual_change.get("asset_id")
                in (
                    change_filter["asset_id"]
                    if isinstance(change_filter.get("asset_id"), list)
                    else [change_filter.get("asset_id")]
                )
            )
        )

        # Role check
        role_check = (
            change_filter.get("role") is None
            or (
                isinstance(change_filter.get("role"), list)
                and len(change_filter["role"]) == 0
            )
            or any(
                r in actual_change.get("roles", [])
                for r in (
                    change_filter["role"]
                    if isinstance(change_filter.get("role"), list)
                    else [change_filter.get("role")]
                )
            )
        )

        # Combine all checks
        return all(
            [
                address_check,
                min_abs_amount_check,
                max_abs_amount_check,
                min_amount_check,
                max_amount_check,
                asset_id_check,
                role_check,
            ]
        )

    return any(
        any(
            check_single_change(cast(dict, actual_change), change_filter)
            for actual_change in transaction_balance_changes
        )
        for change_filter in filtered_balance_changes
    )


def get_subscribed_transactions(  # noqa: C901, PLR0912, PLR0915
    subscription: TransactionSubscriptionParams,
    algod: AlgodClient,
    indexer: IndexerClient | None = None,
) -> TransactionSubscriptionResult:
    """
    Executes a single pull/poll to subscribe to transactions on the configured Algorand
    blockchain for the given subscription context.

    :param subscription: The subscription parameters
    :param algod: The Algod client
    :param indexer: The Indexer client (optional)
    :return: The transaction subscription result
    """
    watermark = subscription["watermark"]
    filters = subscription["filters"]
    max_rounds_to_sync = subscription.get("max_rounds_to_sync") or 500
    sync_behaviour = subscription["sync_behaviour"]
    current_round = subscription.get("current_round") or cast(
        dict[str, Any], algod.status()
    ).get("last-round", 0)
    block_metadata: list[BlockMetadata] | None = None

    # Pre-calculate a flat list of all ARC-28 events to process
    arc28_events: list[Arc28EventToProcess] = [
        {
            "group_name": g["group_name"],
            "event_name": e["name"],
            "event_signature": f"{e['name']}({','.join(a['type'] for a in e['args'])})",
            "event_prefix": hashlib.new(
                "sha512_256",
                f"{e['name']}({','.join(a['type'] for a in e['args'])})".encode(),
            )
            .digest()
            .hex()[:8],
            "event_definition": e,
        }
        for g in (subscription.get("arc28_events") or [])
        for e in g["events"]
    ]

    # Nothing to sync we at the tip of the chain already
    if current_round <= watermark:
        return TransactionSubscriptionResult(
            current_round=current_round,
            starting_watermark=watermark,
            new_watermark=watermark,
            subscribed_transactions=[],
            synced_round_range=(current_round, current_round),
            block_metadata=[],
        )

    indexer_sync_to_round_number = 0
    algod_sync_from_round_number = watermark + 1
    start_round = algod_sync_from_round_number
    end_round = current_round
    catchup_transactions: list[SubscribedTransaction] = []
    start = time.time()
    skip_algod_sync = False

    # If we are less than `max_rounds_to_sync` from the tip of the chain then we consult the `sync_behaviour` to determine what to do
    if current_round - watermark > max_rounds_to_sync:
        if sync_behaviour == "fail":
            raise ValueError(
                f"Invalid round number to subscribe from {algod_sync_from_round_number}; current round number is {current_round}"
            )
        elif sync_behaviour == "skip-sync-newest":  # noqa: RET506
            algod_sync_from_round_number = current_round - max_rounds_to_sync + 1
            start_round = algod_sync_from_round_number
        elif sync_behaviour == "sync-oldest":
            end_round = algod_sync_from_round_number + max_rounds_to_sync - 1
        elif sync_behaviour == "sync-oldest-start-now":
            # When watermark is 0 same behaviour as skip-sync-newest
            if watermark == 0:
                algod_sync_from_round_number = current_round - max_rounds_to_sync + 1
                start_round = algod_sync_from_round_number
            else:
                # Otherwise same behaviour as sync-oldest
                end_round = algod_sync_from_round_number + max_rounds_to_sync - 1
        elif sync_behaviour == "catchup-with-indexer":
            if not indexer:
                raise ValueError("Can't catch up using indexer since it's not provided")

            # If we have more than `max_indexer_rounds_to_sync` rounds to sync from indexer then we skip algod sync and just sync that many rounds from indexer
            indexer_sync_to_round_number = current_round - max_rounds_to_sync
            if (
                subscription.get("max_indexer_rounds_to_sync")
                and indexer_sync_to_round_number - start_round + 1  # type: ignore[operator]
                > subscription["max_indexer_rounds_to_sync"]
            ):
                indexer_sync_to_round_number = (
                    start_round + subscription["max_indexer_rounds_to_sync"] - 1  # type: ignore[operator]
                )
                end_round = indexer_sync_to_round_number
                skip_algod_sync = True
            else:
                algod_sync_from_round_number = indexer_sync_to_round_number + 1

            logger.debug(
                f"Catching up from round {start_round} to round {indexer_sync_to_round_number} via indexer; this may take a few seconds"
            )

            catchup_transactions = []

            # Process transactions in chunks of 30
            for chunked_filters in chunk_array(filters, 30):
                for f in chunked_filters:
                    # Retrieve all pre-filtered transactions from the indexer
                    transactions = search_transactions(
                        indexer,
                        indexer_pre_filter(
                            f["filter"], start_round, indexer_sync_to_round_number
                        ),
                    )

                    # Process each transaction
                    for t in transactions["transactions"]:
                        # Re-run the pre-filter in-memory to properly extract inner transactions
                        filtered_transactions = get_filtered_indexer_transactions(t, f)

                        # Run the post-filter to get the final list of matching transactions
                        post_filtered_transactions = list(
                            filter(
                                lambda x: indexer_post_filter(
                                    f["filter"],
                                    arc28_events,
                                    subscription.get("arc28_events", []),
                                )(x),
                                filtered_transactions,
                            )
                        )

                        catchup_transactions.extend(post_filtered_transactions)

            # Sort by transaction order
            catchup_transactions.sort(
                key=lambda x: (x["confirmed-round"], x["intra-round-offset"])
            )

            # Collapse duplicate transactions
            catchup_transactions = deduplicate_subscribed_transactions(
                catchup_transactions
            )

            logger.debug(
                f"Retrieved {len(catchup_transactions)} transactions from round {start_round} to round "
                f"{algod_sync_from_round_number - 1} via indexer in {(time.time() - start):.3f}s"
            )
        else:
            raise NotImplementedError("Not implemented")

    # Retrieve and process blocks from algod
    algod_transactions: list[SubscribedTransaction] = []
    if not skip_algod_sync:
        start = time.time()
        blocks = get_blocks_bulk(
            {"start_round": algod_sync_from_round_number, "max_round": end_round}, algod
        )
        block_transactions = [
            t for b in blocks for t in get_block_transactions(b["block"])
        ]
        algod_transactions = []
        for f in filters:
            for t in block_transactions:  # type: ignore[assignment]
                if transaction_filter(
                    f["filter"], arc28_events, subscription.get("arc28_events") or []
                )(
                    t  # type: ignore[arg-type]
                ):
                    algod_transactions.append(
                        get_indexer_transaction_from_algod_transaction(t, f["name"])  # type: ignore[arg-type]
                    )

        algod_transactions = deduplicate_subscribed_transactions(algod_transactions)

        block_metadata = [block_data_to_block_metadata(b) for b in blocks]

        logger.debug(
            f"Retrieved {len(block_transactions)} transactions from algod via round(s) {algod_sync_from_round_number}-{end_round} "
            f"in {(time.time() - start):.3f}s"
        )
    else:
        logger.debug(
            f"Skipping algod sync since we have more than {subscription['max_indexer_rounds_to_sync']} rounds to sync from indexer."
        )

    return TransactionSubscriptionResult(
        synced_round_range=(start_round, end_round),
        starting_watermark=watermark,
        new_watermark=end_round,
        current_round=current_round,
        block_metadata=block_metadata or [],
        subscribed_transactions=[
            process_extra_fields(t, arc28_events, subscription.get("arc28_events", []))
            for t in catchup_transactions + algod_transactions
        ],
    )


def process_extra_fields(
    transaction: TransactionResult | SubscribedTransaction,
    arc28_events: list[Arc28EventToProcess],
    arc28_groups: list[Arc28EventGroup],
) -> SubscribedTransaction:
    """
    Process extra fields for a transaction, including ARC-28 events and balance changes.

    :param transaction: The transaction to process
    :param arc28_events: The list of ARC-28 events to process
    :param arc28_groups: The list of ARC-28 event groups
    :return: The processed transaction with extra fields
    """
    groups_to_apply = (
        []
        if transaction["tx-type"] != TransactionType.appl.value
        else [
            g
            for g in arc28_groups
            if transaction_is_in_arc28_event_group(
                g,
                transaction.get("created-application-index")
                or transaction.get("application-transaction", {}).get(
                    "application-id", 0
                ),
                lambda: transaction,
            )
        ]
    )

    events_to_apply = (
        [
            e
            for e in arc28_events
            if any(g["group_name"] == e["group_name"] for g in groups_to_apply)
        ]
        if groups_to_apply
        else []
    )

    arc28_events = extract_arc28_events(
        transaction.get("id", ""),
        [base64.b64decode(log) for log in transaction.get("logs") or []],
        events_to_apply,
        lambda group_name: next(
            g for g in groups_to_apply if g["group_name"] == group_name
        )["continue_on_error"],
    )  # type: ignore[assignment]

    balance_changes = extract_balance_changes_from_indexer_transaction(transaction)

    inner_txns = [
        process_extra_fields(inner, arc28_events, arc28_groups)
        for inner in (transaction.get("inner-txns") or [])
    ]

    return {
        **transaction,
        "arc28_events": arc28_events if len(arc28_events) > 0 else None,  # type: ignore[typeddict-item]
        "balance_changes": balance_changes,
        "inner-txns": inner_txns if len(inner_txns) > 0 else None,  # type: ignore[typeddict-item]
        "filters_matched": transaction.get("filters_matched") or None,  # type: ignore[typeddict-item]
    }


def extract_balance_changes_from_indexer_transaction(  # noqa: PLR0912, C901
    transaction: TransactionResult,
) -> list[BalanceChange]:
    """
    Extract balance changes from an indexer transaction.

    :param transaction: The indexer transaction
    :return: A list of balance changes
    """
    changes: list[BalanceChange] = []

    if transaction["fee"]:
        changes.append(
            {
                "address": transaction["sender"],
                "amount": -transaction["fee"],
                "asset_id": 0,
                "roles": [BalanceChangeRole.Sender],
            }
        )

    if "payment-transaction" in transaction:
        pt = transaction["payment-transaction"]
        sender = transaction["sender"]
        receiver = pt["receiver"]
        amount = pt["amount"]
        close_to = pt.get("close-remainder-to")

        changes.append(
            {
                "address": sender,
                "amount": -amount,
                "asset_id": 0,
                "roles": [BalanceChangeRole.Sender],
            }
        )

        changes.append(
            {
                "address": receiver,
                "amount": amount,
                "asset_id": 0,
                "roles": [BalanceChangeRole.Receiver],
            }
        )

        if close_to:
            changes.append(
                {
                    "address": sender,
                    "amount": -(transaction["closing-amount"] or 0),
                    "asset_id": 0,
                    "roles": [BalanceChangeRole.Sender],
                }
            )

            changes.append(
                {
                    "address": close_to,
                    "amount": (transaction["closing-amount"] or 0),
                    "asset_id": 0,
                    "roles": [BalanceChangeRole.CloseTo],
                }
            )

    if "asset-transfer-transaction" in transaction:
        att = transaction["asset-transfer-transaction"]
        sender = transaction["sender"]
        receiver = att["receiver"]
        amount = att["amount"]
        asset_id = att["asset-id"]
        close_to = att.get("close-to")

        changes.append(
            {
                "address": att.get("sender") or sender,
                "amount": -amount,
                "asset_id": asset_id,
                "roles": [BalanceChangeRole.Sender],
            }
        )

        changes.append(
            {
                "address": receiver,
                "amount": amount,
                "asset_id": asset_id,
                "roles": [BalanceChangeRole.Receiver],
            }
        )

        if close_to:
            changes.append(
                {
                    "address": sender,
                    "amount": -(att["close-amount"] or 0),
                    "asset_id": asset_id,
                    "roles": [BalanceChangeRole.Sender],
                }
            )

            changes.append(
                {
                    "address": close_to,
                    "amount": (att["close-amount"] or 0),
                    "asset_id": asset_id,
                    "roles": [BalanceChangeRole.CloseTo],
                }
            )

    if "asset-config-transaction" in transaction:
        act = transaction["asset-config-transaction"]
        if not act["asset-id"] and transaction.get("created-asset-index"):
            changes.append(
                {
                    "address": transaction["sender"],
                    "amount": act.get("params", {}).get("t", 0),  # type: ignore[typeddict-item]
                    "asset_id": transaction["created-asset-index"],  # type: ignore[typeddict-item]
                    "roles": [BalanceChangeRole.AssetCreator],
                }
            )
        elif act["asset-id"] and not act.get("params"):
            changes.append(
                {
                    "address": transaction["sender"],
                    "amount": 0,
                    "asset_id": act["asset-id"],
                    "roles": [BalanceChangeRole.AssetDestroyer],
                }
            )

    # Deduplicate and consolidate balance changes
    consolidated_changes: list[BalanceChange] = []
    for change in changes:
        existing = None
        for c in consolidated_changes:
            if (
                c["address"] == change["address"]
                and c["asset_id"] == change["asset_id"]
            ):
                existing = c
                break

        if existing:
            existing["amount"] += change["amount"]
            for role in change["roles"]:
                if role not in existing["roles"]:
                    existing["roles"].append(role)
        else:
            consolidated_changes.append(change)

    return consolidated_changes


def get_filtered_indexer_transactions(
    transaction: TransactionResult, txn_filter: NamedTransactionFilter
) -> list[SubscribedTransaction]:
    """
    Process an indexer transaction and return that transaction or any of its inner transactions
    that meet the indexer pre-filter requirements; patching up transaction ID and intra-round-offset on the way through.

    :param transaction: The indexer transaction to process
    :param txn_filter: The named transaction filter to apply
    :return: A list of filtered subscribed transactions
    """
    parent_offset = 0

    def get_parent_offset() -> int:
        nonlocal parent_offset
        parent_offset += 1
        # TODO: Investigate further: I would expect to have to return parent_offset - 1 here, but returning parent_offset works
        return parent_offset

    transactions = [
        {**transaction, "filters_matched": [txn_filter["name"]]},
        *get_indexer_inner_transactions(transaction, transaction, get_parent_offset),
    ]

    return list(
        filter(indexer_pre_filter_in_memory(txn_filter["filter"]), transactions)  # type: ignore[arg-type]
    )


def get_indexer_inner_transactions(
    root: TransactionResult, parent: TransactionResult, offset: Callable
) -> list[SubscribedTransaction]:
    """
    Recursively get inner transactions from an indexer transaction.

    :param root: The root transaction
    :param parent: The parent transaction
    :param offset: A callable to get the parent offset
    :return: A list of subscribed inner transactions
    """
    result = []
    for t in parent.get("inner-txns", []):
        parent_offset = offset()
        result.append(
            cast(
                SubscribedTransaction,
                {
                    **t,
                    "parent_transaction_id": root["id"],
                    "id": f"{root['id']}/inner/{parent_offset + 1}",
                    "intra-round-offset": root["intra-round-offset"]
                    + parent_offset
                    + 1,
                },
            )
        )

    for t in parent.get("inner-txns", []):
        result.extend(get_indexer_inner_transactions(root, t, offset))

    return result


def indexer_post_filter(  # noqa: C901
    subscription: TransactionFilter,
    arc28_events: list[Arc28EventToProcess],
    arc28_event_groups: list[Arc28EventGroup],
) -> Callable[[TransactionResult], bool]:
    """
    Create a post-filter function for indexer transactions based on the subscription parameters.

    :param subscription: The transaction filter parameters
    :param arc28_events: The list of ARC-28 events to process
    :param arc28_event_groups: The list of ARC-28 event groups
    :return: A function that applies the post-filter to a transaction
    """

    def filter_function(t: TransactionResult) -> bool:  # noqa: C901, PLR0912
        result = True
        appl = t.get("application-transaction")

        if subscription.get("asset_create") is True:
            result &= bool(t.get("created-asset-index"))
        elif subscription.get("asset_create") is False:
            result &= not t.get("created-asset-index")

        if subscription.get("app_create") is True:
            result &= bool(t.get("created-application-index"))
        elif subscription.get("app_create") is False:
            result &= not t.get("created-application-index")

        if subscription.get("app_on_complete"):
            if not appl:
                return False

            if isinstance(subscription.get("app_on_complete"), str):
                result &= appl["on-completion"] == subscription.get("app_on_complete")
            else:
                result &= appl["on-completion"] in subscription.get("app_on_complete")  # type: ignore[operator]

        if subscription.get("method_signature"):
            if not appl:
                return False
            method_signature = subscription["method_signature"]
            if isinstance(method_signature, str):
                result &= bool(appl.get("application-args")) and appl[
                    "application-args"
                ][0] == get_method_selector_base64(method_signature)
            else:
                result &= any(
                    appl.get("application-args")
                    and appl["application-args"][0]
                    == get_method_selector_base64(method)
                    for method in method_signature
                )

        if subscription.get("app_call_arguments_match"):
            if not appl:
                return False

            result &= subscription["app_call_arguments_match"](
                [bytes.fromhex(a) for a in appl.get("application-args", [])]
            )

        if subscription.get("arc28_events"):
            if not appl:
                return False

            result &= (
                bool(t.get("application-transaction"))
                and bool(t.get("logs"))
                and has_emitted_matching_arc28_event(
                    t["logs"] or [],
                    arc28_events,
                    arc28_event_groups,
                    subscription["arc28_events"],
                    t.get("created-application-index") or appl.get("application-id", 0),
                    lambda: t,
                )
            )

        if subscription.get("balance_changes"):
            balance_changes = extract_balance_changes_from_indexer_transaction(t)
            result &= has_balance_change_match(
                balance_changes, subscription["balance_changes"]
            )

        if subscription.get("custom_filter"):
            result &= subscription["custom_filter"](t)

        return result

    return filter_function


def transaction_filter(  # noqa: C901, PLR0915
    subscription: TransactionFilter,
    arc28_events: list[Arc28EventToProcess],
    arc28_event_groups: list[Arc28EventGroup],
) -> Callable[[TransactionInBlock], bool]:
    """
    Create a filter function for transactions based on the subscription parameters.

    :param subscription: The transaction filter parameters
    :param arc28_events: The list of ARC-28 events to process
    :param arc28_event_groups: The list of ARC-28 event groups
    :return: A function that applies the filter to a transaction in a block
    """

    def filter_function(  # noqa: C901, PLR0912, PLR0915
        txn: TransactionInBlock,
    ) -> bool:
        t = txn["transaction"].dictify()  # type: ignore[no-untyped-call]
        created_app_id, created_asset_id, logs = (
            txn["created_app_id"],
            txn["created_asset_id"],
            txn["logs"],
        )
        result: bool = True

        if subscription.get("sender"):
            sender = subscription["sender"]
            if isinstance(sender, str):
                result = (
                    result and bool(t.get("snd")) and encode_address(t["snd"]) == sender
                )
            else:
                result = (
                    result and bool(t.get("snd")) and encode_address(t["snd"]) in sender
                )

        if subscription.get("receiver"):
            receiver = subscription["receiver"]
            txn_receiver = t.get("rcv") or t.get("arcv")

            if isinstance(receiver, str):
                result = (
                    result
                    and bool(txn_receiver)
                    and encode_address(txn_receiver) == receiver
                )
            else:
                result = (
                    result
                    and bool(txn_receiver)
                    and encode_address(txn_receiver) in receiver
                )

        if subscription.get("type"):
            txn_type = subscription["type"]
            if isinstance(txn_type, str):
                result = result and t.get("type") == txn_type
            else:
                result = result and bool(t.get("type")) and t["type"] in txn_type

        if subscription.get("note_prefix"):
            result = (
                result
                and bool(t.get("note"))
                and t["note"].decode("utf-8").startswith(subscription["note_prefix"])
            )

        if subscription.get("app_id"):
            app_id = subscription["app_id"]
            if isinstance(app_id, int | float):
                result = result and (
                    t.get("apid") == int(app_id) or created_app_id == int(app_id)
                )
            else:
                app_ids = [int(i) for i in app_id]
                result = result and bool(
                    (t.get("apid") and t["apid"] in app_ids)
                    or bool(created_app_id and created_app_id in app_ids)
                )

        if subscription.get("asset_id"):
            asset_id = subscription["asset_id"]
            if isinstance(asset_id, int):
                result = result and (
                    t.get("xaid") == asset_id or created_asset_id == asset_id
                )
            else:
                asset_ids = [int(i) for i in asset_id]
                result = result and bool(
                    (t.get("xaid") and t["xaid"] in asset_ids)
                    or bool(created_asset_id and created_asset_id in asset_ids)
                )

        txn_amt = t.get("amt") or t.get("aamt", 0)
        if subscription.get("min_amount"):
            result = result and (txn_amt >= subscription["min_amount"])

        if subscription.get("max_amount"):
            result = result and (txn_amt <= subscription["max_amount"])

        if subscription.get("asset_create") is True:
            result = result and bool(created_asset_id)
        elif subscription.get("asset_create") is False:
            result = result and not created_asset_id

        if subscription.get("app_create") is True:
            result = result and bool(created_app_id)
        elif subscription.get("app_create") is False:
            result = result and not created_app_id

        if subscription.get("app_on_complete"):
            app_on_complete = subscription["app_on_complete"]
            on_complete = algod_on_complete_to_indexer_on_complete(
                t.get("apan", 0)
            ).value
            result = result and (
                on_complete
                in (
                    [app_on_complete]
                    if isinstance(app_on_complete, str)
                    else app_on_complete
                )
            )

        if subscription.get("method_signature"):
            method_signature = subscription["method_signature"]
            if isinstance(method_signature, str):
                result = (
                    result
                    and bool(t.get("apaa"))
                    and base64.b64encode(t["apaa"][0]).decode("utf-8")
                    == get_method_selector_base64(method_signature)
                )
            else:
                result = result and any(
                    bool(t.get("apaa"))
                    and base64.b64encode(t["apaa"][0]).decode("utf-8")
                    == get_method_selector_base64(method)
                    for method in method_signature
                )

        if subscription.get("arc28_events"):
            # convert logs (currently utf8 encoded strings) to base64 encoded bytes

            result = result and (
                t.get("type") == TransactionType.appl.value
                and logs is not None
                and has_emitted_matching_arc28_event(
                    [
                        base64.b64encode(
                            log.encode("utf-8", errors="surrogateescape")
                        ).decode("utf-8")
                        for log in logs
                    ],
                    arc28_events,
                    arc28_event_groups,
                    subscription["arc28_events"],
                    created_app_id or t.get("apid", 0),
                    lambda: get_indexer_transaction_from_algod_transaction(txn),
                )
            )

        if subscription.get("app_call_arguments_match"):
            result = result and subscription["app_call_arguments_match"](t.get("apaa"))

        if subscription.get("balance_changes"):
            balance_changes = extract_balance_changes_from_block_transaction(
                txn["block_transaction"]
            )
            result = result and has_balance_change_match(
                balance_changes, subscription["balance_changes"]
            )

        if subscription.get("custom_filter"):
            result = result and subscription["custom_filter"](
                get_indexer_transaction_from_algod_transaction(txn)
            )

        return result

    return filter_function
