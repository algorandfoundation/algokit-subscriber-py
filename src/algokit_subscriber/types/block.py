from typing import Any, TypedDict

from algosdk.transaction import Transaction
from typing_extensions import NotRequired  # noqa: UP035


class BlockValueDelta(TypedDict):
    """A value delta as a result of a block transaction"""

    action_type: int
    """
    DeltaAction is an enum of actions that may be performed when applying a delta to a TEAL key/value store:
      * `1`: SetBytesAction indicates that a TEAL byte slice should be stored at a key
      * `2`: SetUintAction indicates that a Uint should be stored at a key
      * `3`: DeleteAction indicates that the value for a particular key should be deleted
    """

    bytes_value: NotRequired[bytes]
    """Bytes value"""

    uint_value: NotRequired[int]
    """Uint64 value"""


class BlockTransactionEvalDelta(TypedDict):
    """Eval deltas for a block"""

    gd: dict[str, BlockValueDelta]
    """The delta of global state, keyed by key"""

    ld: dict[int, dict[str, BlockValueDelta]]
    """The delta of local state keyed by account ID offset in [txn.Sender, ...txn.Accounts] and then keyed by key"""

    lg: list[str]
    """Logs"""

    itx: NotRequired[list["BlockInnerTransaction"]]
    """Inner transactions"""


# TODO: Typing
LogicSig = dict[str, Any]

# TODO: Typing
MultisigSig = dict[str, Any]


class TransactionInBlock(TypedDict):
    """
    The representation of all important data for a single transaction or inner transaction
    and its side effects within a committed block.
    """

    block_transaction: "BlockTransaction | BlockInnerTransaction"
    """The block data for the transaction"""

    round_offset: int
    """
    The offset of the transaction within the round including inner transactions.

    @example
    - 0
    - 1
    - 2
    - 3
    - 4
    - 5
    """

    round_index: int
    """
    The index within the block.txns array of this transaction or if it's an inner transaction of it's ultimate parent transaction.

    @example
    - 0
    - 1
    - 1
    - 1
    - 1
    - 2
    """

    parent_transaction_id: NotRequired[None | str]
    """
    The ID of the parent transaction if this is an inner transaction.
    """

    parent_offset: NotRequired[None | int]
    """
    The offset within the parent transaction.

    @example
    - `None`
    - `None`
    - 0
    - 1
    - 2
    - `None`
    """

    genesis_hash: bytes
    """The binary genesis hash of the network the transaction is within."""

    genesis_id: str
    """The string genesis ID of the network the transaction is within."""

    round_number: int
    """The round number of the block the transaction is within."""

    round_timestamp: int
    """The round unix timestamp of the block the transaction is within."""

    transaction: Transaction
    """The transaction as an algosdk `Transaction` object."""

    created_asset_id: NotRequired[None | int]
    """The asset ID if an asset was created from this transaction."""

    created_app_id: NotRequired[None | int]
    """The app ID if an app was created from this transaction."""

    asset_close_amount: NotRequired[None | int]
    """The asset close amount if the sender asset position was closed from this transaction."""

    close_amount: NotRequired[None | int]
    """The ALGO close amount if the sender account was closed from this transaction."""

    logs: NotRequired[None | list[str]]
    """Any logs that were issued as a result of this transaction."""


class BlockInnerTransaction(TypedDict):
    # TODO: Typing
    txn: dict[str, Any]
    """The encoded transaction data"""

    dt: NotRequired[None | BlockTransactionEvalDelta]
    """The eval deltas for the block"""

    caid: NotRequired[None | int]
    """Asset ID when an asset is created by the transaction"""

    apid: NotRequired[None | int]
    """App ID when an app is created by the transaction"""

    aca: NotRequired[None | int]
    """Asset closing amount in decimal units"""

    ca: NotRequired[None | int]
    """Algo closing amount in microAlgos"""

    sig: NotRequired[None | bytes]
    """Transaction ED25519 signature"""

    lsig: NotRequired[None | LogicSig]
    """Logic signature"""

    msig: NotRequired[None | MultisigSig]
    """Transaction multisig signature"""

    sgnr: NotRequired[None | bytes]
    """The signer, if signing with a different key than the Transaction type `from` property indicates"""


class BlockTransaction(BlockInnerTransaction):
    """
    Data that is returned in a raw Algorand block for a single transaction

    @see https://github.com/algorand/go-algorand/blob/master/data/transactions/signedtxn.go#L32
    """

    hgi: NotRequired[None | bool]
    """Has genesis id"""

    hgh: NotRequired[None | bool]
    """Has genesis hash"""


# TODO: Typing
BlockAgreementCertificate = dict[str, Any]


class Block(TypedDict):
    """
    Data that is returned in a raw Algorand block.

    @see https://github.com/algorand/go-algorand/blob/master/data/bookkeeping/block.go#L32
    """

    earn: int
    """
    RewardsLevel specifies how many rewards, in MicroAlgos, have
    been distributed to each config.Protocol.RewardUnit of MicroAlgos
    since genesis.
    """

    fees: bytes
    """The FeeSink accepts transaction fees. It can only spend to the incentive pool."""

    frac: int
    """
    The number of leftover MicroAlgos after the distribution of RewardsRate/rewardUnits
    MicroAlgos for every reward unit in the next round.
    """

    gen: str
    """Genesis ID to which this block belongs."""

    gh: bytes
    """Genesis hash to which this block belongs."""

    prev: NotRequired[None | bytes]
    """The hash of the previous block"""

    proto: str
    """UpgradeState tracks the protocol upgrade state machine; proto is the current protocol."""

    rate: NotRequired[None | int]
    """The number of new MicroAlgos added to the participation stake from rewards at the next round."""

    rnd: int
    """Round number."""

    rwcalr: int
    """The round at which the RewardsRate will be recalculated."""

    rwd: bytes
    """
    The RewardsPool accepts periodic injections from the
    FeeSink and continually redistributes them to addresses as rewards.
    """

    seed: bytes
    """Sortition seed"""

    tc: int
    """
    TxnCounter is the number of the next transaction that will be
    committed after this block. Genesis blocks can start at either
    0 or 1000, depending on a consensus parameter (AppForbidLowResources).
    """

    ts: int
    """Round time (unix timestamp)"""

    txn: bytes
    """
    Root of transaction merkle tree using SHA512_256 hash function.
    This commitment is computed based on the PaysetCommit type specified in the block's consensus protocol.
    """

    txn256: str
    """
    Root of transaction vector commitment merkle tree using SHA256 hash function.
    """

    nextproto: NotRequired[None | str]
    """
    The next proposed protocol version.
    """

    nextyes: NotRequired[None | int]
    """
    Number of blocks which approved the protocol upgrade.
    """

    nextbefore: NotRequired[None | int]
    """
    Deadline round for this protocol upgrade (No votes will be considered after this round).
    """

    nextswitch: NotRequired[None | int]
    """
    Round on which the protocol upgrade will take effect.
    """

    txns: NotRequired[None | list[BlockTransaction]]
    """
    The transactions within the block.
    """


class BlockData(TypedDict):
    """
    Data that is returned in a raw Algorand block.
    """

    block: Block
    """The block itself."""

    cert: BlockAgreementCertificate
    """cert (BlockAgreementCertificate): The block certification."""
