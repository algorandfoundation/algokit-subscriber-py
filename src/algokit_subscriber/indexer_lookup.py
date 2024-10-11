# Assuming these types are defined elsewhere or imported from a types module
from collections.abc import Callable
from typing import Any

from algosdk.v2client.indexer import IndexerClient

from .types.indexer import (
    AccountLookupResult,
    ApplicationCreatedLookupResult,
    ApplicationResult,
    AssetBalancesLookupResult,
    LookupAssetHoldingsOptions,
    MiniAssetHolding,
    TransactionLookupResult,
    TransactionResult,
    TransactionSearchResults,
)

DEFAULT_INDEXER_MAX_API_RESOURCES_PER_ACCOUNT = 1000


def transaction(transaction_id: str, indexer: IndexerClient) -> TransactionLookupResult:
    """
    Looks up a transaction by ID using Indexer.
    """
    return indexer.transaction(txid=transaction_id)  # type: ignore[no-untyped-call, no-any-return]


def lookup_account_by_address(
    account_address: str, indexer: IndexerClient
) -> AccountLookupResult:
    """
    Looks up an account by address using Indexer.
    """
    return indexer.account_info(address=account_address)  # type: ignore[no-untyped-call, no-any-return]


def lookup_account_created_application_by_address(
    indexer: IndexerClient,
    address: str,
    get_all: bool | None = None,
    pagination_limit: int | None = None,
) -> list[ApplicationResult]:
    """
    Looks up applications that were created by the given address; will automatically paginate through all data.
    """

    def extract_items(
        response: ApplicationCreatedLookupResult,
    ) -> list[ApplicationResult]:
        if "message" in response:
            raise Exception({"status": 404, **response})
        return response["applications"]

    def build_request(next_token: str | None = None) -> dict[str, Any]:
        args: dict[str, Any] = {
            "address": address,
            "include-all": get_all,
            "limit": pagination_limit or DEFAULT_INDEXER_MAX_API_RESOURCES_PER_ACCOUNT,
        }

        if next_token:
            args["next_token"] = next_token

        return args

    return execute_paginated_request(
        indexer.lookup_account_application_by_creator, extract_items, build_request
    )


def lookup_asset_holdings(
    indexer: IndexerClient,
    asset_id: int,
    options: LookupAssetHoldingsOptions | None = None,
    pagination_limit: int | None = None,
) -> list[MiniAssetHolding]:
    """
    Looks up asset holdings for the given asset; will automatically paginate through all data.
    """

    def extract_items(response: AssetBalancesLookupResult) -> list[MiniAssetHolding]:
        if "message" in response:
            raise Exception({"status": 404, **response})
        return response["balances"]

    def build_request(next_token: str | None = None) -> dict[str, Any]:
        args: dict[str, Any] = {
            "asset-id": asset_id,
            "limit": pagination_limit or DEFAULT_INDEXER_MAX_API_RESOURCES_PER_ACCOUNT,
            "include-all": (
                options["include-all"] if options and "include-all" in options else None
            ),
            "currency-greater-than": (
                options["currency-greater-than"]
                if options and "currency-greater-than" in options
                else None
            ),
            "currency-less-than": (
                options["currency-less-than"]
                if options and "currency-less-than" in options
                else None
            ),
        }

        if next_token:
            args["next-token"] = next_token

        return args

    return execute_paginated_request(
        indexer.lookup_account_assets, extract_items, build_request
    )


def search_transactions(
    indexer: IndexerClient,
    search_criteria: dict[str, Any],
    pagination_limit: int | None = None,
) -> TransactionSearchResults:
    """
    Allows transactions to be searched for the given criteria.
    """
    current_round = 0

    def extract_items(response: TransactionSearchResults) -> list[TransactionResult]:
        nonlocal current_round
        if "message" in response:
            raise Exception({"status": 404, **response})
        if response["current-round"] > current_round:
            current_round = response["current-round"]
        return response["transactions"]

    def build_request(next_token: str | None = None) -> dict[str, Any]:
        args: dict[str, Any] = search_criteria
        args["limit"] = (
            pagination_limit or DEFAULT_INDEXER_MAX_API_RESOURCES_PER_ACCOUNT
        )
        if next_token:
            args["next_page"] = next_token

        return args

    transactions = execute_paginated_request(
        indexer.search_transactions, extract_items, build_request
    )

    return {
        "current-round": current_round,
        "next-token": "",
        "transactions": transactions,
    }


def execute_paginated_request(
    method: Callable,
    extract_items: Callable[[Any], list[Any]],
    build_request: Callable[[str | None], dict[str, Any]],
) -> list[Any]:
    """
    Executes a paginated request and returns all results.
    """
    results = []
    next_token = None

    while True:
        request = build_request(next_token)
        response = method(**request)
        items = extract_items(response)
        if not items:
            break
        results.extend(items)
        next_token = response.get("next-token")
        if not next_token:
            break

    return results
