from enum import Enum
from typing import Any, TypedDict

from typing_extensions import NotRequired  # noqa: UP035

# TODO: Typing
TealKeyValue = dict[str, Any]

TransactionSearchResults = TypedDict(
    "TransactionSearchResults",
    {
        "current-round": int,
        "next-token": str,
        "transactions": list["TransactionResult"],
    },
)

AccountLookupResult = TypedDict(
    "AccountLookupResult", {"current-round": int, "account": "AccountResult"}
)

AssetsLookupResult = TypedDict(
    "AssetsLookupResult",
    {"current-round": int, "next-token": str, "assets": list["AssetHolding"]},
)

AssetsCreatedLookupResult = TypedDict(
    "AssetsCreatedLookupResult",
    {"current-round": int, "next-token": str, "assets": list["AssetResult"]},
)

ApplicationCreatedLookupResult = TypedDict(
    "ApplicationCreatedLookupResult",
    {
        "current-round": int,
        "next-token": str,
        "applications": list["ApplicationResult"],
    },
)

AssetLookupResult = TypedDict(
    "AssetLookupResult", {"current-round": int, "asset": "AssetResult"}
)

LookupAssetHoldingsOptions = TypedDict(
    "LookupAssetHoldingsOptions",
    {
        "currency-less-than": NotRequired[float],
        "currency-greater-than": NotRequired[float],
        "include-all": NotRequired[bool],
    },
)

AssetBalancesLookupResult = TypedDict(
    "AssetBalancesLookupResult",
    {"current-round": int, "next-token": str, "balances": list["MiniAssetHolding"]},
)

TransactionLookupResult = TypedDict(
    "TransactionLookupResult",
    {"current-round": int, "transaction": "TransactionResult"},
)

ApplicationLookupResult = TypedDict(
    "ApplicationLookupResult",
    {"current-round": int, "application": "ApplicationResult"},
)

TransactionResult = TypedDict(
    "TransactionResult",
    {
        "id": str,
        "tx-type": str,
        "fee": int,
        "sender": str,
        "first-valid": int,
        "last-valid": int,
        "confirmed-round": NotRequired[int],
        "group": NotRequired[None | str],
        "note": NotRequired[str],
        "logs": NotRequired[list[str] | None],
        "round-time": NotRequired[int],
        "intra-round-offset": NotRequired[int],
        "signature": NotRequired["TransactionSignature"],
        "application-transaction": NotRequired["ApplicationTransactionResult"],
        "created-application-index": NotRequired[None | int],
        "asset-config-transaction": NotRequired["AssetConfigTransactionResult"],
        "created-asset-index": NotRequired[None | int],
        "asset-freeze-transaction": NotRequired["AssetFreezeTransactionResult"],
        "asset-transfer-transaction": NotRequired["AssetTransferTransactionResult"],
        "keyreg-transaction": NotRequired["KeyRegistrationTransactionResult"],
        "payment-transaction": NotRequired["PaymentTransactionResult"],
        "state-proof-transaction": NotRequired["StateProofTransactionResult"],
        "auth-addr": NotRequired[None | str],
        "closing-amount": NotRequired[None | int],
        "genesis-hash": NotRequired[str],
        "genesis-id": NotRequired[str],
        "inner-txns": NotRequired[list["TransactionResult"]],
        "rekey-to": NotRequired[str],
        "lease": NotRequired[str],
        "local-state-delta": NotRequired[list[dict]],
        "global-state-delta": NotRequired[list[dict]],
        "receiver-rewards": NotRequired[int],
        "sender-rewards": NotRequired[int],
        "close-rewards": NotRequired[int],
    },
)

AccountResult = TypedDict(
    "AccountResult",
    {
        "address": str,
        "amount": int,
        "amount-without-pending-rewards": int,
        "apps-local-state": NotRequired[list["AppLocalState"]],
        "apps-total-extra-pages": NotRequired[int],
        "apps-total-schema": NotRequired["StateSchema"],
        "assets": NotRequired[list["AssetHolding"]],
        "auth-addr": NotRequired[str],
        "closed-at-round": NotRequired[int],
        "created-apps": NotRequired[list["ApplicationResult"]],
        "created-assets": NotRequired[list["AssetResult"]],
        "created-at-round": NotRequired[int],
        "deleted": NotRequired[bool],
        "participation": NotRequired["AccountParticipation"],
        "pending-rewards": int,
        "reward-base": NotRequired[int],
        "rewards": int,
        "round": int,
        "sig-type": "SignatureType",
        "status": "AccountStatus",
        "total-apps-opted-in": int,
        "total-assets-opted-in": int,
        "total-box-bytes": int,
        "total-boxes": int,
        "total-created-apps": int,
        "total-created-assets": int,
    },
)

PaymentTransactionResult = TypedDict(
    "PaymentTransactionResult",
    {
        "amount": int,
        "close-amount": NotRequired[None | int],
        "close-remainder-to": NotRequired[None | str],
        "receiver": str,
    },
)

StateProofTransactionResult = TypedDict(
    "StateProofTransactionResult",
    {
        "message": "StateProofMessage",
        "state-proof": "StateProof",
        "state-proof-type": int,
    },
)

StateProofMessage = TypedDict(
    "StateProofMessage",
    {
        "block-headers-commitment": str,
        "first-attested-round": int,
        "latest-attested-round": int,
        "ln-proven-weight": int,
        "voters-commitment": str,
    },
)

StateProof = TypedDict(
    "StateProof",
    {
        "part-proofs": "MerkleArrayProof",
        "positions-to-reveal": list[int],
        "reveals": list["StateProofReveal"],
        "salt-version": int,
        "sig-commit": str,
        "sig-proofs": "MerkleArrayProof",
        "signed-weight": int,
    },
)

StateProofReveal = TypedDict(
    "StateProofReveal",
    {
        "position": int,
        "participant": "StateProofParticipant",
        "sig-slot": "StateProofSigSlot",
    },
)


class StateProofParticipant(TypedDict):
    verifier: "StateProofVerifier"
    weight: int


StateProofVerifier = TypedDict(
    "StateProofVerifier", {"commitment": str, "key-lifetime": int}
)

StateProofSigSlot = TypedDict(
    "StateProofSigSlot", {"lower-sig-weight": int, "signature": "MerkleSignature"}
)

MerkleSignature = TypedDict(
    "MerkleSignature",
    {
        "falcon-signature": str,
        "merkle-array-index": int,
        "proof": "MerkleArrayProof",
        "verifying-key": str,
    },
)

MerkleArrayProof = TypedDict(
    "MerkleArrayProof",
    {"hash-factory": "HashFactory", "path": list[str], "tree-depth": int},
)

HashFactory = TypedDict("HashFactory", {"hash-type": int})

ApplicationTransactionResult = TypedDict(
    "ApplicationTransactionResult",
    {
        "accounts": NotRequired[list[str]],
        "application-args": NotRequired[list[str]],
        "application-id": int,
        "foreign-apps": NotRequired[list[int]],
        "foreign-assets": NotRequired[list[int]],
        "on-completion": str,
        "approval-program": NotRequired[str],
        "clear-state-program": NotRequired[str],
        "extra-program-pages": NotRequired[int | None],
    },
)

AssetConfigTransactionResult = TypedDict(
    "AssetConfigTransactionResult",
    {"asset-id": int, "params": NotRequired["AssetParams"]},
)

AssetFreezeTransactionResult = TypedDict(
    "AssetFreezeTransactionResult",
    {"address": str, "asset-id": int, "new-freeze-status": bool},
)

AssetTransferTransactionResult = TypedDict(
    "AssetTransferTransactionResult",
    {
        "amount": int,
        "asset-id": int,
        "close-amount": NotRequired[None | int],
        "close-to": NotRequired[None | str],
        "receiver": str,
        "sender": NotRequired[None | str],
    },
)

KeyRegistrationTransactionResult = TypedDict(
    "KeyRegistrationTransactionResult",
    {
        "non-participation": NotRequired[bool],
        "selection-participation-key": NotRequired[str],
        "state-proof-key": NotRequired[str],
        "vote-first-valid": NotRequired[int],
        "vote-key-dilution": NotRequired[int],
        "vote-last-valid": NotRequired[int],
        "vote-participation-key": NotRequired[str],
    },
)

AssetResult = TypedDict(
    "AssetResult",
    {
        "index": int,
        "deleted": NotRequired[bool],
        "created-at-round": NotRequired[int],
        "destroyed-at-round": NotRequired[int],
        "params": "AssetParams",
    },
)

ApplicationResult = TypedDict(
    "ApplicationResult",
    {
        "id": int,
        "params": "ApplicationParams",
        "created-at-round": NotRequired[int],
        "deleted": NotRequired[bool],
        "deleted-at-round": NotRequired[int],
    },
)


class TransactionSignature(TypedDict):
    logicsig: NotRequired["LogicTransactionSignature"]
    multisig: NotRequired["MultisigTransactionSignature"]
    sig: NotRequired[str]


LogicTransactionSignature = TypedDict(
    "LogicTransactionSignature",
    {
        "args": NotRequired[list[str]],
        "logic": str,
        "multisig-signature": NotRequired["MultisigTransactionSignature"],
        "signature": NotRequired[str],
    },
)


class MultisigTransactionSignature(TypedDict):
    subsignature: list["MultisigTransactionSubSignature"]
    threshold: int
    version: int


MultisigTransactionSubSignature = TypedDict(
    "MultisigTransactionSubSignature",
    {"public-key": str, "signature": NotRequired[str]},
)


class EvalDelta(TypedDict):
    action: int
    bytes: NotRequired[str]
    uint: NotRequired[int]


ApplicationParams = TypedDict(
    "ApplicationParams",
    {
        "creator": str,
        "approval-program": str,
        "clear-state-program": str,
        "extra-program-pages": NotRequired[int],
        "global-state": list["TealKeyValue"],
        "global-state-schema": NotRequired["StateSchema"],
        "local-state-schema": NotRequired["StateSchema"],
    },
)

StateSchema = TypedDict("StateSchema", {"num-byte-slice": int, "num-uint": int})


class ApplicationOnComplete(Enum):
    noop = "noop"
    optin = "optin"
    closeout = "closeout"
    clear = "clear"
    update = "update"
    delete = "delete"


AssetParams = TypedDict(
    "AssetParams",
    {
        "creator": str,
        "decimals": int,
        "total": int,
        "clawback": NotRequired[str],
        "default-frozen": NotRequired[bool],
        "freeze": NotRequired[str],
        "manager": NotRequired[str],
        "metadata-hash": NotRequired[bytes],
        "name": NotRequired[str],
        "name-b64": NotRequired[bytes],
        "reserve": NotRequired[str],
        "unit-name": NotRequired[str],
        "unit-name-b64": NotRequired[bytes],
        "url": NotRequired[str],
        "url-b64": NotRequired[bytes],
    },
)


class SignatureType(Enum):
    sig = "sig"
    msig = "msig"
    lsig = "lsig"


class AccountStatus(Enum):
    Offline = "Offline"
    Online = "Online"
    NotParticipating = "NotParticipating"


AccountParticipation = TypedDict(
    "AccountParticipation",
    {
        "selection-participation-key": str,
        "state-proof-key": NotRequired[str],
        "vote-first-valid": int,
        "vote-key-dilution": int,
        "vote-last-valid": int,
        "vote-participation-key": str,
    },
)

AppLocalState = TypedDict(
    "AppLocalState",
    {
        "closed-out-at-round": NotRequired[int],
        "deleted": NotRequired[bool],
        "id": int,
        "key-value": NotRequired[list["TealKeyValue"]],
        "opted-in-at-round": NotRequired[int],
        "schema": "StateSchema",
    },
)

AssetHolding = TypedDict(
    "AssetHolding",
    {
        "amount": int,
        "asset-id": int,
        "deleted": NotRequired[bool],
        "is-frozen": bool,
        "opted-in-at-round": int,
        "opted-out-at-round": int,
    },
)

MiniAssetHolding = TypedDict(
    "MiniAssetHolding",
    {
        "address": str,
        "amount": int,
        "deleted": NotRequired[bool],
        "is-frozen": bool,
        "opted-in-at-round": NotRequired[int],
        "opted-out-at-round": NotRequired[int],
    },
)
