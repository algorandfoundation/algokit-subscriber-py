import base64
import dataclasses
import itertools
import logging
import time
import typing
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import Any

from algokit_algod_client import AlgodClient
from algokit_indexer_client import IndexerClient
from algokit_indexer_client.models import Transaction

from algokit_subscriber._block import get_blocks_bulk
from algokit_subscriber._indexer_lookup import search_transactions
from algokit_subscriber._internal_types import CompiledFilter, IndexerTransactionFilter
from algokit_subscriber._transform import (
    block_data_to_block_metadata,
    get_block_transactions,
)
from algokit_subscriber._utils import method_selector_bytes
from algokit_subscriber.types.arc28 import (
    Arc28Event,
    Arc28EventFilter,
    Arc28EventGroup,
    EmittedArc28Event,
)
from algokit_subscriber.types.subscription import (
    BalanceChange,
    BalanceChangeFilter,
    BalanceChangeRole,
    BlockMetadata,
    NamedTransactionFilter,
    SubscribedTransaction,
    TransactionFilter,
    TransactionSubscriptionParams,
    TransactionSubscriptionResult,
)

SearchForTransactions = dict[str, Any]

logger = logging.getLogger(__package__)


_Filter = Callable[[Transaction], bool]


def compile_filters(
    filters: Sequence[NamedTransactionFilter],
    arc28_events: list[Arc28EventGroup] | None = None,
) -> list[CompiledFilter]:
    """
    Pre-compile transaction filters for efficient reuse across multiple subscription polls.
    Can be optionally provided to get_subscribed_transactions.

    :param filters: The transaction filters to compile
    :param arc28_events: Optional ARC-28 event group definitions
    :return: A list of compiled filters
    """
    arc28_groups = arc28_events or []
    compiled = []
    for named_filter in filters:
        pre_filter = _create_indexer_pre_filter(named_filter.filter)
        post_filter = _create_transaction_filter(named_filter.filter, arc28_groups)
        compiled.append(
            CompiledFilter(name=named_filter.name, pre_filter=pre_filter, post_filter=post_filter)
        )
    return compiled


_MAX_SAFE_JSON_INTEGER = 2**53 - 1


def _create_indexer_pre_filter(
    subscription: TransactionFilter,
) -> IndexerTransactionFilter:
    """
    Create a pre-filter for the Indexer client based on the subscription parameters.

    :param subscription: The transaction filter parameters
    :return: A IndexerTransactionFilter of pre-filter arguments for the Indexer client
    """
    # NOTE: everything in this method needs to be mirrored to `indexer_pre_filter_in_memory` below
    args = IndexerTransactionFilter()

    if subscription.sender and isinstance(subscription.sender, str):
        args.address = subscription.sender
        args.address_role = "sender"

    if subscription.receiver and isinstance(subscription.receiver, str):
        args.address = subscription.receiver
        args.address_role = "receiver"

    if subscription.type and isinstance(subscription.type, str):
        args.tx_type = subscription.type

    if subscription.note_prefix:
        if isinstance(subscription.note_prefix, bytes):
            note_prefix = subscription.note_prefix
        else:
            note_prefix = subscription.note_prefix.encode("utf-8")

        args.note_prefix = base64.b64encode(note_prefix).decode("utf-8")

    if subscription.app_id and isinstance(subscription.app_id, int):
        args.application_id = subscription.app_id

    if subscription.asset_id and isinstance(subscription.asset_id, int):
        args.asset_id = subscription.asset_id

    # Indexer only supports min_amount and maxAmount for non-payments if an
    # asset ID is provided so check we are looking for just payments, or we
    # have provided asset ID before adding to pre-filter. If they aren't added
    # here they will be picked up in the in-memory pre-filter
    if subscription.min_amount and (subscription.type == "pay" or subscription.asset_id):
        # Indexer only supports numbers, but even though this is less precise
        # the in-memory indexer pre-filter will remove any false positives
        args.min_amount = min(subscription.min_amount - 1, _MAX_SAFE_JSON_INTEGER)

    if (
        subscription.max_amount
        and subscription.max_amount < _MAX_SAFE_JSON_INTEGER
        and (
            subscription.type == "pay"
            or (subscription.asset_id and (subscription.min_amount or 0) > 0)
        )
    ):
        args.max_amount = subscription.max_amount + 1

    return args


def get_subscribed_transactions(  # noqa: C901, PLR0912, PLR0915
    subscription: TransactionSubscriptionParams,
    algod: AlgodClient,
    indexer: IndexerClient | None = None,
    *,
    compiled_filters: list[CompiledFilter] | None = None,
) -> TransactionSubscriptionResult:
    """
    Executes a single pull/poll to subscribe to transactions on the configured Algorand
    blockchain for the given subscription context.

    :param subscription: The subscription parameters
    :param algod: The Algod client
    :param indexer: The Indexer client (optional)
    :param compiled_filters: Pre-compiled filters to use. If not provided, filters will be
        compiled from subscription.filters. For repeated polling, pre-compile once using
        compile_filters() and pass here for better performance.
    :return: The transaction subscription result
    """
    watermark = subscription.watermark
    max_rounds_to_sync = subscription.max_rounds_to_sync
    sync_behaviour = subscription.sync_behaviour
    current_round = subscription.current_round or algod.status().last_round
    block_metadata: list[BlockMetadata] | None = None

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

    algod_sync_from_round_number = watermark + 1
    start_round = algod_sync_from_round_number
    end_round = current_round
    catchup_transactions = list[SubscribedTransaction]()
    start = time.time()
    skip_algod_sync = False

    arc28_groups = subscription.arc28_events or []
    filters = compiled_filters or compile_filters(subscription.filters, subscription.arc28_events)

    # If we are less than `max_rounds_to_sync` from the tip of the chain then
    # we consult the `sync_behaviour` to determine what to do
    if current_round - watermark > max_rounds_to_sync:
        if sync_behaviour == "fail":
            raise ValueError(
                f"Invalid round number to subscribe from "
                f"{algod_sync_from_round_number}; current round number is {current_round}"
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

            # If we have more than `max_indexer_rounds_to_sync` rounds to sync
            # from indexer then we skip algod sync and just sync that many
            # rounds from indexer
            indexer_sync_to_round_number = current_round - max_rounds_to_sync
            if (
                subscription.max_indexer_rounds_to_sync
                and indexer_sync_to_round_number - start_round + 1
                > subscription.max_indexer_rounds_to_sync
            ):
                indexer_sync_to_round_number = (
                    start_round + subscription.max_indexer_rounds_to_sync - 1
                )
                end_round = indexer_sync_to_round_number
                skip_algod_sync = True
            else:
                algod_sync_from_round_number = indexer_sync_to_round_number + 1

            logger.debug(
                f"Catching up from round {start_round} to round "
                f"{indexer_sync_to_round_number} via indexer; this may take a few seconds"
            )

            catchup_transactions = []

            # Process transactions in chunks of 30
            for chunked_filters in itertools.batched(filters, 30):
                for f in chunked_filters:
                    # Retrieve all pre-filtered transactions from the indexer
                    transactions = search_transactions(
                        indexer,
                        f.pre_filter,
                        min_round=start_round,
                        max_round=indexer_sync_to_round_number,
                    )
                    subscribed_txns = _map_txn_and_inner_txns_to_subscribed_txn(transactions)

                    # Run the post-filter to get the final list of matching transactions
                    for t in subscribed_txns:
                        if f.post_filter(t):
                            t.filters_matched.append(f.name)
                    catchup_transactions.extend(t for t in subscribed_txns if t.filters_matched)

            # Sort by transaction order
            catchup_transactions.sort(key=lambda x: (x.confirmed_round, x.intra_round_offset))

            # Collapse duplicate transactions
            catchup_transactions = _deduplicate_subscribed_transactions(catchup_transactions)

            logger.debug(
                f"Retrieved {len(catchup_transactions)} transactions from round "
                f"{start_round} to round {algod_sync_from_round_number - 1} "
                f"via indexer in {(time.time() - start):.3f}s"
            )
        else:
            typing.assert_never(sync_behaviour)

    # Retrieve and process blocks from algod
    algod_transactions = list[SubscribedTransaction]()
    if not skip_algod_sync:
        start = time.time()
        blocks = get_blocks_bulk(algod_sync_from_round_number, end_round, algod)
        fetch_end = time.time()
        block_transactions = [t for b in blocks for t in get_block_transactions(b.block)]
        subscribed_txns = _map_txn_and_inner_txns_to_subscribed_txn(block_transactions)
        mapping_end = time.time()
        for f in filters:
            # Process each transaction
            for t in subscribed_txns:
                if f.post_filter(t):
                    t.filters_matched.append(f.name)

        algod_transactions = [t for t in subscribed_txns if t.filters_matched]
        filtering_end = time.time()
        block_metadata = [block_data_to_block_metadata(b) for b in blocks]
        block_meta = time.time() - filtering_end
        filtering = filtering_end - mapping_end
        mapping = mapping_end - fetch_end
        fetch = fetch_end - start

        logger.debug(
            f"Retrieved {len(block_transactions)} transactions from algod via "
            f"round(s) {algod_sync_from_round_number}-{end_round} "
            f"in {(time.time() - start):.3f}s"
            f" {fetch=}, {mapping=}, {filtering=}, {block_meta=}"
        )
    else:
        logger.debug(
            f"Skipping algod sync since we have more than "
            f"{subscription.max_indexer_rounds_to_sync} rounds to sync from indexer."
        )

    return TransactionSubscriptionResult(
        synced_round_range=(start_round, end_round),
        starting_watermark=watermark,
        new_watermark=end_round,
        current_round=current_round,
        block_metadata=block_metadata or [],
        subscribed_transactions=[
            _process_extra_fields(t, arc28_groups)
            for t in catchup_transactions + algod_transactions
        ],
    )


def _deduplicate_subscribed_transactions(
    txns: list[SubscribedTransaction],
) -> list[SubscribedTransaction]:
    """
    Deduplicate subscribed transactions based on their ID.

    :param txns: List of subscribed transactions
    :return: Deduplicated list of subscribed transactions
    """
    result_dict = dict[str, SubscribedTransaction]()

    for txn in txns:
        try:
            existing_txn = result_dict[txn.id_]
        except KeyError:
            result_dict[txn.id_] = dataclasses.replace(
                txn, filters_matched=txn.filters_matched.copy()
            )
        else:
            existing_txn.filters_matched.extend(txn.filters_matched)
    return list(result_dict.values())


def _process_extra_fields(
    transaction: SubscribedTransaction,
    arc28_groups: list[Arc28EventGroup],
) -> SubscribedTransaction:
    """
    Process extra fields for a transaction, including ARC-28 events and balance changes.

    :param transaction: The transaction to process
    :param arc28_groups: The ARC-28 event groups
    :return: The processed transaction with extra fields
    """
    arc28_events = _extract_arc28_events(transaction, arc28_groups)
    balance_changes = _extract_balance_changes_from_indexer_transaction(transaction)
    inner_txns = [_process_extra_fields(inner, arc28_groups) for inner in transaction.inner_txns]

    return dataclasses.replace(
        transaction,
        arc28_events=arc28_events,
        balance_changes=balance_changes,
        inner_txns=inner_txns,
    )


def _extract_arc28_events(
    transaction: SubscribedTransaction, groups: list[Arc28EventGroup]
) -> list[EmittedArc28Event]:
    arc28_events = list[EmittedArc28Event]()
    logs = transaction.logs or []
    if not logs:
        return arc28_events

    potential_groups = []
    for group in groups:
        group_filter = _create_arc28_group_filter(group)
        if all(f(transaction) for f in group_filter):
            potential_groups.append(group)

    for log in logs:
        for group in potential_groups:
            for event in group.events:
                if not log.startswith(event.prefix):
                    continue
                event_bytes = log[4:]
                arc28_event = _extract_arc28_event(
                    transaction.id_, event_bytes, group.group_name, group, event
                )
                if arc28_event is not None:
                    arc28_events.append(arc28_event)
    return arc28_events


def _extract_arc28_event(
    transaction_id: str,
    event_bytes: bytes,
    group_name: str,
    group: Arc28EventGroup,
    event: Arc28Event,
) -> EmittedArc28Event | None:
    try:
        value = event.abi_type.decode(event_bytes)
    except (ValueError, TypeError) as ex:
        if group.continue_on_error:
            logger.warning(
                f"Warning: Encountered error while processing "
                f"{group_name}.{event.name} on transaction {transaction_id}: {ex}"
            )
            return None
        raise

    args = list[Any]()
    args_by_name = dict[str, Any]()

    for arg, arg_value in zip(event.args, value, strict=True):
        args.append(arg_value)
        if arg.name:
            args_by_name[arg.name] = arg_value

    return EmittedArc28Event(
        group_name=group_name,
        event_name=event.name,
        event_signature=event.signature,
        event_prefix=event.prefix.hex(),
        event_definition=event,
        args=args,
        args_by_name=args_by_name,
    )


def _extract_balance_changes_from_indexer_transaction(  # noqa: PLR0912, C901
    transaction: Transaction,
) -> list[BalanceChange]:
    """
    Extract balance changes from an indexer transaction.

    :param transaction: The indexer transaction
    :return: A list of balance changes
    """
    changes = list[BalanceChange]()

    if transaction.fee:
        changes.append(
            BalanceChange(
                address=transaction.sender,
                amount=-transaction.fee,
                asset_id=0,
                roles=[BalanceChangeRole.Sender],
            )
        )

    pay = transaction.payment_transaction
    if pay:
        sender = transaction.sender
        receiver = pay.receiver
        amount = pay.amount
        close_to = pay.close_remainder_to
        changes.append(
            BalanceChange(
                address=sender,
                amount=-amount,
                asset_id=0,
                roles=[BalanceChangeRole.Sender],
            )
        )
        changes.append(
            BalanceChange(
                address=receiver,
                amount=amount,
                asset_id=0,
                roles=[BalanceChangeRole.Receiver],
            )
        )

        if close_to:
            closing_amount = transaction.closing_amount or 0
            changes.append(
                BalanceChange(
                    address=sender,
                    amount=-closing_amount,
                    asset_id=0,
                    roles=[BalanceChangeRole.Sender],
                )
            )
            changes.append(
                BalanceChange(
                    address=close_to,
                    amount=closing_amount,
                    asset_id=0,
                    roles=[BalanceChangeRole.CloseTo],
                )
            )

    asset_xfer = transaction.asset_transfer_transaction
    if asset_xfer:
        sender = transaction.sender
        receiver = asset_xfer.receiver
        amount = asset_xfer.amount
        asset_id = asset_xfer.asset_id
        close_to = asset_xfer.close_to

        changes.append(
            BalanceChange(
                address=asset_xfer.sender or sender,
                amount=-amount,
                asset_id=asset_id,
                roles=[BalanceChangeRole.Sender],
            )
        )

        changes.append(
            BalanceChange(
                address=receiver,
                amount=amount,
                asset_id=asset_id,
                roles=[BalanceChangeRole.Receiver],
            )
        )

        if close_to:
            close_amount = asset_xfer.close_amount or 0
            changes.append(
                BalanceChange(
                    address=sender,
                    amount=-close_amount,
                    asset_id=asset_id,
                    roles=[BalanceChangeRole.Sender],
                )
            )

            changes.append(
                BalanceChange(
                    address=close_to,
                    amount=close_amount,
                    asset_id=asset_id,
                    roles=[BalanceChangeRole.CloseTo],
                )
            )

    asset_config = transaction.asset_config_transaction
    if asset_config:
        if not asset_config.asset_id and transaction.created_asset_id:
            changes.append(
                BalanceChange(
                    address=transaction.sender,
                    amount=asset_config.params.total if asset_config.params else 0,
                    asset_id=transaction.created_asset_id,
                    roles=[BalanceChangeRole.AssetCreator],
                )
            )
        elif asset_config.asset_id and not asset_config.params:
            changes.append(
                BalanceChange(
                    address=transaction.sender,
                    amount=0,
                    asset_id=asset_config.asset_id,
                    roles=[BalanceChangeRole.AssetDestroyer],
                )
            )

    # Deduplicate and consolidate balance changes
    consolidated_changes = dict[tuple[str, int], BalanceChange]()
    for change in changes:
        key = (change.address, change.asset_id)
        try:
            existing = consolidated_changes[key]
        except KeyError:
            consolidated_changes[key] = change
        else:
            existing.amount += change.amount
            for role in change.roles:
                if role not in existing.roles:
                    existing.roles.append(role)

    return list(consolidated_changes.values())


def _map_txn_and_inner_txns_to_subscribed_txn(
    transactions: list[Transaction],
) -> list[SubscribedTransaction]:
    """
    Process an indexer transaction and return that transaction or any of its
    inner transactions that meet the indexer pre-filter requirements; patching
    up transaction ID and intra-round-offset on the way through.

    :param transactions: The indexer transactions to process
    :return: A list of filtered subscribed transactions
    """
    result = []
    for transaction in transactions:
        root_offset = itertools.count(1)
        root_txn = _txn_to_subscribed_txn(
            transaction,
            filters_matched=[],
            inner_txns=_map_inner_txns(transaction, transaction, root_offset),
            parent_intra_round_offset=transaction.intra_round_offset,
        )
        result.append(root_txn)
        result.extend(_expand_inner_txns(root_txn))
    return result


def _expand_inner_txns(txn: SubscribedTransaction) -> Iterable[SubscribedTransaction]:
    for inner_txn in txn.inner_txns:
        yield inner_txn
        yield from _expand_inner_txns(inner_txn)


_TRANSACTION_FIELDS = [f.name for f in dataclasses.fields(Transaction)]


def _txn_to_subscribed_txn(instance: Transaction, **changes: Any) -> SubscribedTransaction:
    fields = {field_name: getattr(instance, field_name) for field_name in _TRANSACTION_FIELDS}
    fields.update(changes)
    return SubscribedTransaction(**fields)


def _map_inner_txns(
    root: Transaction, parent: Transaction, root_offset_iter: Iterator[int]
) -> list[SubscribedTransaction]:
    result = []
    for inner_txn in parent.inner_txns or []:
        root_offset = next(root_offset_iter)
        inner_txns = _map_inner_txns(root, inner_txn, root_offset_iter)
        result.append(
            _txn_to_subscribed_txn(
                inner_txn,
                id_=f"{root.id_}/inner/{root_offset}",
                parent_transaction_id=root.id_,
                intra_round_offset=(root.intra_round_offset or 0) + root_offset,
                parent_intra_round_offset=root.intra_round_offset,
                inner_txns=inner_txns,
            )
        )
    return result


def _get_txn_receiver(txn: Transaction) -> str | None:
    if txn.payment_transaction:
        return txn.payment_transaction.receiver
    elif txn.asset_transfer_transaction:
        return txn.asset_transfer_transaction.receiver
    else:
        return None


def _get_txn_app_id(txn: Transaction) -> int | None:
    if txn.application_transaction:
        return txn.created_app_id or txn.application_transaction.application_id
    else:
        return None


def _get_txn_asset_id(txn: Transaction) -> int | None:
    if txn.created_asset_id:
        return txn.created_asset_id
    elif txn.asset_transfer_transaction:
        return txn.asset_transfer_transaction.asset_id
    elif txn.asset_config_transaction:
        return txn.asset_config_transaction.asset_id
    elif txn.asset_freeze_transaction:
        return txn.asset_freeze_transaction.asset_id
    else:
        return None


def _get_txn_amount(txn: Transaction) -> int:
    if txn.asset_transfer_transaction:
        return txn.asset_transfer_transaction.amount
    elif txn.payment_transaction:
        return txn.payment_transaction.amount
    else:
        return 0


def _get_txn_on_complete(txn: Transaction) -> str | None:
    if txn.application_transaction:
        return txn.application_transaction.on_completion.value
    else:
        return None


def _get_txn_app_args(txn: Transaction) -> list[bytes] | None:
    if txn.application_transaction:
        return txn.application_transaction.application_args
    else:
        return None


def _get_txn_method_selector(txn: Transaction) -> bytes | None:
    args = _get_txn_app_args(txn)
    return args[0] if args else None


def _make_set[T](maybe_seq: T | list[T]) -> set[T]:
    if isinstance(maybe_seq, list):
        return set(maybe_seq)
    else:
        return {maybe_seq}


def _create_transaction_filter(  # noqa: C901, PLR0912, PLR0915
    transaction_filter: TransactionFilter,
    arc28_groups: list[Arc28EventGroup],
) -> Callable[[Transaction], bool]:
    """
    Create a filter function for transactions based on the subscription parameters.

    :param transaction_filter: The transaction filter parameters
    :param arc28_groups: The ARC-28 group definitions
    :return: A function that applies the filter to a transaction in a block
    """
    filters = list[_Filter]()
    if transaction_filter.sender:
        senders = _make_set(transaction_filter.sender)
        filters.append(lambda t: t.sender in senders)

    if transaction_filter.receiver:
        receivers = _make_set(transaction_filter.receiver)
        filters.append(lambda t: _get_txn_receiver(t) in receivers)

    if transaction_filter.type:
        txn_types = _make_set(transaction_filter.type)  # type: ignore[arg-type]
        filters.append(lambda t: t.tx_type in txn_types)

    if transaction_filter.note_prefix:
        if isinstance(transaction_filter.note_prefix, bytes):
            note_prefix_bytes = transaction_filter.note_prefix
        else:
            note_prefix_bytes = transaction_filter.note_prefix.encode("utf-8")
        filters.append(lambda t: (t.note or b"").startswith(note_prefix_bytes))

    if transaction_filter.app_id:
        app_ids = _make_set(transaction_filter.app_id)
        filters.append(lambda t: _get_txn_app_id(t) in app_ids)

    if transaction_filter.asset_id:
        asset_ids = _make_set(transaction_filter.asset_id)
        filters.append(lambda t: _get_txn_asset_id(t) in asset_ids)

    if transaction_filter.min_amount:
        min_amount = transaction_filter.min_amount
        filters.append(lambda t: _get_txn_amount(t) >= min_amount)

    if transaction_filter.max_amount:
        max_amount = transaction_filter.max_amount
        filters.append(lambda t: _get_txn_amount(t) <= max_amount)

    if transaction_filter.asset_create is True:
        filters.append(lambda t: bool(t.created_asset_id))
    elif transaction_filter.asset_create is False:
        filters.append(lambda t: not t.created_asset_id)

    if transaction_filter.app_create is True:
        filters.append(lambda t: bool(t.created_app_id))
    elif transaction_filter.app_create is False:
        filters.append(lambda t: not t.created_app_id)

    if transaction_filter.app_on_complete:
        app_on_complete = _make_set(transaction_filter.app_on_complete)
        filters.append(lambda t: _get_txn_on_complete(t) in app_on_complete)

    if transaction_filter.method_signature:
        method_signatures = {
            method_selector_bytes(sig) for sig in _make_set(transaction_filter.method_signature)
        }
        filters.append(lambda t: _get_txn_method_selector(t) in method_signatures)

    if transaction_filter.arc28_events:
        filter_ = _create_arc28_filter(arc28_groups, transaction_filter.arc28_events)
        filters.append(filter_)

    if transaction_filter.app_call_arguments_match:
        app_args_match = transaction_filter.app_call_arguments_match
        filters.append(lambda t: app_args_match(_get_txn_app_args(t)))

    if transaction_filter.balance_changes:
        balance_filter = _create_balance_changes_filter(transaction_filter.balance_changes)
        filters.append(balance_filter)

    if transaction_filter.custom_filter:
        filters.append(transaction_filter.custom_filter)

    if len(filters) == 0:
        return lambda _: True
    elif len(filters) == 1:
        return filters[0]
    else:
        return lambda t: all(txn_filter(t) for txn_filter in filters)


def _create_arc28_filter(
    groups: list[Arc28EventGroup], event_filters: list[Arc28EventFilter]
) -> _Filter:
    filtered_groups_events = defaultdict[str, list[Arc28Event]](list)
    group_event_filter = {(f.group_name, f.event_name) for f in event_filters}
    groups_by_name = {g.group_name: g for g in groups}
    for group in groups:
        for event in group.events:
            if (group.group_name, event.name) in group_event_filter:
                filtered_groups_events[group.group_name].append(event)
    group_filters = [
        _create_arc28_group_event_filter(groups_by_name[group_name], events)
        for group_name, events in filtered_groups_events.items()
    ]
    return lambda t: any(group_filter(t) for group_filter in group_filters)


def _create_arc28_group_filter(self: Arc28EventGroup) -> list[_Filter]:
    filters = list[_Filter]()
    if self.process_for_app_ids:
        app_ids = set(self.process_for_app_ids)
        filters.append(lambda t: _get_txn_app_id(t) in app_ids)
    if self.process_transaction:
        filters.append(self.process_transaction)
    return filters


def _create_arc28_group_event_filter(group: Arc28EventGroup, events: list[Arc28Event]) -> _Filter:
    filters = _create_arc28_group_filter(group)

    event_prefixes = tuple(e.prefix for e in events)

    def log_filter(txn: Transaction) -> bool:
        logs = txn.logs or []
        return any(log.startswith(event_prefixes) for log in logs)

    filters.append(log_filter)

    return lambda t: all(f(t) for f in filters)


_BalanceChangeFilter = Callable[[BalanceChange], bool]
_BalanceChangeFilterSet = list[_BalanceChangeFilter]


def _create_balance_changes_filter(
    balance_changes_filters: list[BalanceChangeFilter],
) -> _Filter:
    filter_sets = list[_BalanceChangeFilterSet]()

    for balance_change_filter in balance_changes_filters:
        filter_set = _create_balance_change_filter_set(balance_change_filter)
        if filter_set:
            filter_sets.append(filter_set)

    def txn_filter(txn: Transaction) -> bool:
        balance_changes = _extract_balance_changes_from_indexer_transaction(txn)
        for balance_change in balance_changes:
            for filter_set in filter_sets:
                if all(filter_(balance_change) for filter_ in filter_set):
                    return True
        return False

    return txn_filter


def _create_balance_change_filter_set(
    balance_change_filter: BalanceChangeFilter,
) -> _BalanceChangeFilterSet:
    filter_set = _BalanceChangeFilterSet()

    if balance_change_filter.address:
        addresses = _make_set(balance_change_filter.address)
        filter_set.append(lambda bc: bc.address in addresses)

    if balance_change_filter.asset_id is not None:
        asset_ids = _make_set(balance_change_filter.asset_id)
        filter_set.append(lambda bc: bc.asset_id in asset_ids)

    if balance_change_filter.role:
        roles = set(_make_set(balance_change_filter.role))
        filter_set.append(lambda bc: bool(roles.intersection(bc.roles)))

    # don't need to filter if None or 0
    if balance_change_filter.min_absolute_amount:
        min_abs_amount = balance_change_filter.min_absolute_amount
        filter_set.append(lambda bc: abs(bc.amount) >= min_abs_amount)

    # a max of 0 would eliminate everything, so only test for None
    if balance_change_filter.max_absolute_amount is not None:
        max_abs_amount = balance_change_filter.max_absolute_amount
        filter_set.append(lambda bc: abs(bc.amount) <= max_abs_amount)

    if balance_change_filter.min_amount is not None:
        min_amount = balance_change_filter.min_amount
        filter_set.append(lambda bc: bc.amount >= min_amount)

    if balance_change_filter.max_amount is not None:
        max_amount = balance_change_filter.max_amount
        filter_set.append(lambda bc: bc.amount <= max_amount)

    return filter_set
