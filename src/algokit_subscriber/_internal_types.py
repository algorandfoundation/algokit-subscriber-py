from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from algokit_indexer_client.models import Transaction


@dataclass
class IndexerTransactionFilter:
    note_prefix: str | None = None
    tx_type: str | None = None
    sig_type: str | None = None
    group_id: str | None = None
    txid: str | None = None
    round_: int | None = None
    asset_id: int | None = None
    before_time: datetime | None = None
    after_time: datetime | None = None
    currency_greater_than: int | None = None
    currency_less_than: int | None = None
    address: str | None = None
    address_role: str | None = None
    exclude_close_to: bool | None = None
    rekey_to: bool | None = None
    application_id: int | None = None
    min_amount: int | None = None
    max_amount: int | None = None


@dataclass
class CompiledFilter:
    """A pre-compiled filter for efficient transaction matching."""

    name: str
    """The name of the filter."""

    pre_filter: IndexerTransactionFilter
    """The pre-filter for indexer queries."""

    post_filter: Callable[[Transaction], bool]
    """The post-filter function for in-memory filtering."""
