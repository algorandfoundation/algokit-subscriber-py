import typing
from collections.abc import Callable

from algokit_indexer_client import IndexerClient, models

from algokit_subscriber._internal_types import IndexerTransactionFilter

DEFAULT_INDEXER_MAX_API_RESOURCES_PER_ACCOUNT = 1000
_TItem = typing.TypeVar("_TItem")
_TItemsAndPage = tuple[list[_TItem], str | None]


def lookup_account_created_application_by_address(
    indexer: IndexerClient,
    address: str,
    *,
    get_all: bool | None = None,
    pagination_limit: int = DEFAULT_INDEXER_MAX_API_RESOURCES_PER_ACCOUNT,
) -> list[models.Application]:
    """
    Looks up applications that were created by the given address; will
    automatically paginate through all data.
    """

    def request(
        next_token: str | None = None,
    ) -> _TItemsAndPage:
        response = indexer.lookup_account_created_applications(
            address,
            include_all=get_all,
            limit=pagination_limit,
            next_=next_token,
        )
        return response.applications, response.next_token

    return execute_paginated_request(request)


def lookup_asset_holdings(  # noqa: PLR0913
    indexer: IndexerClient,
    asset_id: int,
    *,
    get_all: bool | None = None,
    currency_greater_than: int | None = None,
    currency_less_than: int | None = None,
    pagination_limit: int = DEFAULT_INDEXER_MAX_API_RESOURCES_PER_ACCOUNT,
) -> list[models.MiniAssetHolding]:
    """
    Looks up asset holdings for the given asset; will automatically paginate through all data.
    """

    def request(
        next_token: str | None = None,
    ) -> _TItemsAndPage:
        response = indexer.lookup_asset_balances(
            asset_id=asset_id,
            limit=pagination_limit,
            include_all=get_all,
            currency_greater_than=currency_greater_than,
            currency_less_than=currency_less_than,
            next_=next_token,
        )
        return response.balances, response.next_token

    return execute_paginated_request(request)


def search_transactions(
    indexer: IndexerClient,
    transaction_filter: IndexerTransactionFilter,
    *,
    min_round: int,
    max_round: int,
    pagination_limit: int = DEFAULT_INDEXER_MAX_API_RESOURCES_PER_ACCOUNT,
) -> list[models.Transaction]:
    """
    Allows transactions to be searched for the given criteria.
    """

    def request(next_token: str | None = None) -> _TItemsAndPage:
        response = indexer.search_for_transactions(
            limit=pagination_limit,
            next_=next_token,
            note_prefix=transaction_filter.note_prefix,
            tx_type=transaction_filter.tx_type,
            sig_type=transaction_filter.sig_type,
            group_id=transaction_filter.group_id,
            txid=transaction_filter.txid,
            round_=transaction_filter.round_,
            min_round=min_round,
            max_round=max_round,
            asset_id=transaction_filter.asset_id,
            before_time=transaction_filter.before_time,
            after_time=transaction_filter.after_time,
            currency_greater_than=transaction_filter.currency_greater_than,
            currency_less_than=transaction_filter.currency_less_than,
            address=transaction_filter.address,
            address_role=transaction_filter.address_role,
            exclude_close_to=transaction_filter.exclude_close_to,
            rekey_to=transaction_filter.rekey_to,
            application_id=transaction_filter.application_id,
        )
        return response.transactions, response.next_token

    return execute_paginated_request(request)


def execute_paginated_request(
    request_callback: Callable[[str | None], _TItemsAndPage],
) -> list[_TItem]:
    """
    Executes a paginated request and returns all results.
    """
    results = []
    next_token = None

    while True:
        items, next_token = request_callback(next_token)
        if not items:
            break
        results.extend(items)
        if not next_token:
            break

    return results
