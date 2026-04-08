from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from algokit_indexer_client.models import Transaction

from algokit_subscriber.types.arc28 import Arc28EventFilter, Arc28EventGroup, EmittedArc28Event


class BalanceChangeRole(Enum):
    Sender = "Sender"
    Receiver = "Receiver"
    CloseTo = "CloseTo"
    AssetCreator = "AssetCreator"
    AssetDestroyer = "AssetDestroyer"


@dataclass(kw_only=True, slots=True)
class BlockRewards:
    fee_sink: str
    """
    FeeSink is an address that accepts transaction fees, it can only spend to
    the incentive pool.
    """

    rewards_calculation_round: int
    """
    number of leftover MicroAlgos after the distribution of rewards-rate
    MicroAlgos for every reward unit in the next round.
    """

    rewards_level: int
    """
    How many rewards, in MicroAlgos, have been distributed to each RewardUnit
    of MicroAlgos since genesis.
    """

    rewards_pool: str
    """
    RewardsPool is an address that accepts periodic injections from the
    fee-sink and continually redistributes them as rewards.
    """

    rewards_rate: int
    """
    Number of new MicroAlgos added to the participation stake from rewards at
    the next round.
    """

    rewards_residue: int
    """
    Number of leftover MicroAlgos after the distribution of
    RewardsRate/rewardUnits MicroAlgos for every reward unit in the next round.
    """


@dataclass(kw_only=True, slots=True)
class BlockUpgradeState:
    current_protocol: str
    """Current protocol version"""

    next_protocol: str | None = None
    """The next proposed protocol version."""

    next_protocol_approvals: int | None = None
    """Number of blocks which approved the protocol upgrade."""

    next_protocol_vote_before: int | None = None
    """Deadline round for this protocol upgrade (No votes will be consider after this round)."""

    next_protocol_switch_on: int | None = None
    """Round on which the protocol upgrade will take effect."""


@dataclass(kw_only=True, slots=True)
class BlockStateProofTracking:
    """Tracks the status of state proofs."""

    next_round: int | None = None
    """Next round for which we will accept a state proof transaction."""

    online_total_weight: int | None = None
    """
    The total number of microalgos held by the online accounts during the
    StateProof round.
    """

    type: int | None = None
    """State Proof Type. Note the raw object uses map with this as key."""

    voters_commitment: str | None = None
    """Root of a vector commitment containing online accounts that will help sign the proof."""


@dataclass(kw_only=True, slots=True)
class BlockUpgradeVote:
    """Fields relating to voting for a protocol upgrade."""

    upgrade_approve: bool | None = None
    """Indicates a yes vote for the current proposal."""

    upgrade_delay: int | None = None
    """Indicates the time between acceptance and execution."""

    upgrade_propose: str | None = None
    """Indicates a proposed upgrade."""


@dataclass(kw_only=True, slots=True)
class ParticipationUpdates:
    """Participation account data that needs to be checked/acted on by the network."""

    absent_participation_accounts: list[str] | None = None
    """A list of online accounts that need to be suspended."""

    expired_participation_accounts: list[str] | None = None
    """
    A list of online accounts that needs to be converted to offline
    since their participation key expired.
    """


@dataclass(kw_only=True, slots=True)
class BlockMetadata:
    """Metadata about a block that was retrieved from algod."""

    hash: str | None = None
    """The base64 block hash."""

    round: int
    """The round of the block."""

    timestamp: int
    """Block creation timestamp in seconds since epoch"""

    genesis_id: str
    """The genesis ID of the chain."""

    genesis_hash: str
    """The base64 genesis hash of the chain."""

    previous_block_hash: str | None = None
    """The base64 previous block hash."""

    seed: str
    """The base64 seed of the block."""

    rewards: BlockRewards | None = None
    """Fields relating to rewards"""

    parent_transaction_count: int
    """Count of parent transactions in this block"""

    full_transaction_count: int
    """Full count of transactions and inner transactions (recursively) in this block."""

    txn_counter: int
    """
    Number of the next transaction that will be committed after this block.
    It is 0 when no transactions have ever been committed (since TxnCounter
    started being supported).
    """

    transactions_root: str
    """
    Root of transaction merkle tree using SHA512_256 hash function (base64 encoded).
    This commitment is computed based on the PaysetCommit type specified in
    the block's consensus protocol.
    """

    transactions_root_sha256: str
    """
    TransactionsRootSHA256 is an auxiliary TransactionRoot, built using a
    vector commitment instead of a merkle tree, and SHA256 hash function
    instead of the default SHA512_256 (base64 encoded). This commitment can be used on
    environments where only the SHA256 function exists.
    """

    upgrade_state: BlockUpgradeState | None = None
    """Fields relating to a protocol upgrade."""

    state_proof_tracking: list[BlockStateProofTracking] | None = None
    """Tracks the status of state proofs."""

    upgrade_vote: BlockUpgradeVote | None = None
    """Fields relating to voting for a protocol upgrade."""

    participation_updates: ParticipationUpdates | None = None
    """Participation account data that needs to be checked/acted on by the network."""

    proposer: str | None = None
    """Address of the proposer of this block."""


@dataclass(kw_only=True, slots=True)
class BalanceChange:
    """Represents a balance change effect for a transaction."""

    address: str
    """The address that the balance change is for."""

    asset_id: int
    """The asset ID of the balance change, or 0 for Algos."""

    amount: int
    """The amount of the balance change in smallest divisible unit or microAlgos."""

    roles: list[BalanceChangeRole]
    """The roles the account was playing that led to the balance change"""


@dataclass(kw_only=True, slots=True)
class SubscribedTransaction(Transaction):
    """
    The common model used to expose a transaction that is returned from a
    subscription.

    Substantively, based on the Indexer `TransactionResult` model format with
    some modifications to:

    * Add the `parent_transaction_id` field so inner transactions have a
      reference to their parent
    * Override the type of `inner_txns` to be `SubscribedTransaction[]` so
      inner transactions (recursively) get these extra fields too
    * Add emitted ARC-28 events via `arc28_events`
    * Balance changes in algo or assets
    """

    id_: str
    inner_txns: "list[SubscribedTransaction]"  # type: ignore[assignment]
    parent_transaction_id: str | None = None
    """
    The transaction ID of the parent of this transaction (if it's an inner
    transaction).
    """
    parent_intra_round_offset: int | None = None

    arc28_events: list[EmittedArc28Event] = field(default_factory=list)
    """Any ARC-28 events emitted from an app call."""

    filters_matched: list[str] = field(default_factory=list)
    """
    The names of any filters that matched the given transaction to result in
    it being 'subscribed'.
    """

    balance_changes: list[BalanceChange] = field(default_factory=list)
    """The balance changes in the transaction."""


@dataclass(kw_only=True, slots=True)
class TransactionSubscriptionResult:
    """The result of a single subscription pull/poll."""

    synced_round_range: tuple[int, int]
    """The round range that was synced from/to"""

    current_round: int
    """The current detected tip of the configured Algorand blockchain."""

    starting_watermark: int
    """The watermark value that was retrieved at the start of the subscription poll."""

    new_watermark: int
    """
    The new watermark value to persist for the next call to
    `get_subscribed_transactions` to continue the sync.
    Will be equal to `synced_round_range[1]`. Only persist this
    after processing (or in the same atomic transaction as)
    subscribed transactions to keep it reliable.
    """

    subscribed_transactions: list[SubscribedTransaction]
    """
    Any transactions that matched the given filter within
    the synced round range. This substantively uses the indexer transaction
    format to represent the data with some additional fields.
    """

    block_metadata: list[BlockMetadata] | None = None
    """
    The metadata about any blocks that were retrieved from algod as part
    of the subscription poll.
    """


@dataclass(kw_only=True, slots=True)
class BeforePollMetadata:
    """Metadata about an impending subscription poll."""

    watermark: int
    """The current watermark of the subscriber"""

    current_round: int
    """The current round of algod"""


@dataclass(kw_only=True, slots=True)
class BalanceChangeFilter:
    asset_id: int | list[int] | None = None
    """
    Match transactions with balance changes for one of the given asset ID(s),
    with Algo being `0`
    """
    role: BalanceChangeRole | list[BalanceChangeRole] | None = None
    """
    Match transactions with balance changes for an account with one of the
    given role(s)
    """
    address: str | list[str] | None = None
    """Match transactions with balance changes affecting one of the given account(s)"""
    min_absolute_amount: int | float | None = None
    """
    Match transactions with absolute (i.e. using math.abs()) balance changes
    being greater than or equal to the given minimum (microAlgos or decimal units of an ASA
    """
    max_absolute_amount: int | float | None = None
    """
    Match transactions with absolute (i.e. using math.abs()) balance changes
    being less than or equal to the given maximum (microAlgos or decimal units of an ASA
    """
    min_amount: int | float | None = None
    """
    Match transactions with balance changes
    being greater than or equal to the given minimum (microAlgos or decimal units of an ASA)
    """
    max_amount: int | float | None = None
    """
    Match transactions with balance changes
    being less than or equal to the given maximum (microAlgos or decimal units of an ASA)
    """


TransactionType = Literal["pay", "axfer", "afrz", "acfg", "keyreg", "appl", "stpf", "hb"]


@dataclass(kw_only=True, slots=True)
class TransactionFilter:
    """Specify a filter to apply to find transactions of interest."""

    type: TransactionType | list[TransactionType] | None = None
    """Filter based on the given transaction type(s)."""

    sender: str | list[str] | None = None
    """Filter to transactions sent from the specified address(es)."""

    receiver: str | list[str] | None = None
    """Filter to transactions being received by the specified address(es)."""

    note_prefix: str | bytes | None = None
    """Filter to transactions with a note having the given prefix."""

    app_id: int | list[int] | None = None
    """Filter to transactions against the app with the given ID(s)."""

    app_create: bool | None = None
    """Filter to transactions that are creating an app."""

    app_on_complete: str | list[str] | None = None
    """Filter to transactions that have given on complete(s)."""

    asset_id: int | list[int] | None = None
    """Filter to transactions against the asset with the given ID(s)."""

    asset_create: bool | None = None
    """Filter to transactions that are creating an asset."""

    min_amount: int | None = None
    """
    Filter to transactions where the amount being transferred is greater
    than or equal to the given minimum (microAlgos or decimal units of an ASA if type: axfer).
    """

    max_amount: int | None = None
    """
    Filter to transactions where the amount being transferred is less than
    or equal to the given maximum (microAlgos or decimal units of an ASA if type: axfer).
    """

    method_signature: str | list[str] | None = None
    """
    Filter to app transactions that have the given ARC-0004 method selector(s) for
    the given method signature as the first app argument.
    """

    app_call_arguments_match: Callable[[list[bytes] | None], bool] | None = None
    """Filter to app transactions that meet the given app arguments predicate."""

    arc28_events: list[Arc28EventFilter] | None = None
    """
    Filter to app transactions that emit the given ARC-28 events.
    Note: the definitions for these events must be passed in to the
    subscription config via `arc28_events`.
    """

    balance_changes: list[BalanceChangeFilter] | None = None
    """
    Filter to transactions that result in balance changes that match one or
    more of the given set of balance changes.
    """

    custom_filter: Callable[[Transaction], bool] | None = None
    """Catch-all custom filter to filter for things that the rest of the filters don't provide."""


SyncBehaviour = Literal[
    "catchup-with-indexer", "fail", "skip-sync-newest", "sync-oldest", "sync-oldest-start-now"
]


@dataclass(kw_only=True, slots=True)
class NamedTransactionFilter:
    """Specify a named filter to apply to find transactions of interest."""

    name: str
    """The name to give the filter."""

    filter: TransactionFilter
    """The filter itself."""


@dataclass(kw_only=True, slots=True)
class CoreTransactionSubscriptionParams:
    filters: Sequence[NamedTransactionFilter]
    """The filter(s) to apply to find transactions of interest."""

    arc28_events: list[Arc28EventGroup] | None = None
    """Any ARC-28 event definitions to process from app call logs."""

    max_rounds_to_sync: int = 500
    """
    The maximum number of rounds to sync from algod for each subscription pull/poll.
    Defaults to 500.
    """

    max_indexer_rounds_to_sync: int | None = None
    """
    The maximum number of rounds to sync from indexer when using
    `sync_behaviour: 'catchup-with-indexer'`.
    """

    sync_behaviour: SyncBehaviour
    """
    If the current tip of the configured Algorand blockchain is more than
    `max_rounds_to_sync` past `watermark` then how should that be handled.

    `fail`: Immediately fail
    `skip-sync-newest`: Skip catchup and start syncing from the latest block
        regardless of the watermark.
    `sync-oldest`: Start syncing from the watermark
    `sync-oldest-start-now`: If the watermark is 0, start syncing from round 0.
        Otherwise skip to the latest block.
    `catchup-with-indexer`: Use indexer to get missing transactions that match
        the filters starting from the watermark. Filters will be used in the
        indexer request to reduce the total amount of requests needed
        (relative to getting every block)
    """


@dataclass(kw_only=True, slots=True)
class TransactionSubscriptionParams(CoreTransactionSubscriptionParams):
    watermark: int
    """
    The current round watermark that transactions have previously been synced to.
    """

    current_round: int | None = None
    """
    The current tip of the configured Algorand blockchain.
    If not provided, it will be resolved on demand.
    """


@dataclass(kw_only=True, slots=True)
class WatermarkPersistence:
    get: Callable[[], int | None]
    """Method to retrieve the current watermark"""

    set: Callable[[int], None]
    """Method to persist the new watermark"""


@dataclass(kw_only=True, slots=True)
class SubscriberConfigFilter(NamedTransactionFilter):
    """A single event to subscribe to / emit."""

    mapper: Callable[[list[SubscribedTransaction]], list[Any]] | None = None
    """
    An optional data mapper if you want the event data to take a certain shape
    when subscribing to events with this filter name.
    """


@dataclass(kw_only=True, slots=True)
class AlgorandSubscriberConfig(CoreTransactionSubscriptionParams):
    """
    Configuration for the subscriber.
    """

    filters: Sequence[SubscriberConfigFilter]
    """The set of filters to subscribe to / emit events for, along with optional data mappers."""

    watermark_persistence: WatermarkPersistence
    """
    Methods to retrieve and persist the current watermark so syncing is resilient and maintains
    its position in the chain
    """
    frequency_in_seconds: float | None = None
    """The frequency to poll for new blocks in seconds; defaults to 1s"""

    wait_for_block_when_at_tip: bool | None = None
    """
    Whether to wait via algod `/status/wait-for-block-after` endpoint when at
    the tip of the chain; reduces latency of subscription
    """
