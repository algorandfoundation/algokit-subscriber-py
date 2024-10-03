import base64
import hashlib
from collections import OrderedDict
from collections.abc import Callable, Sequence
from typing import Any, TypedDict, cast

import msgpack  # type: ignore[import-untyped]
from algosdk.transaction import (
    ApplicationCallTxn,
    AssetConfigTxn,
    AssetFreezeTxn,
    AssetTransferTxn,
    KeyregTxn,
    PaymentTxn,
    StateProofTxn,
    Transaction,
)
from typing_extensions import NotRequired  # noqa: UP035

from .types.block import (
    Block,
    BlockData,
    BlockInnerTransaction,
    BlockTransaction,
    TransactionInBlock,
)
from .types.indexer import TransactionResult
from .types.subscription import (
    BalanceChange,
    BalanceChangeRole,
    BlockMetadata,
    SubscribedTransaction,
)
from .types.transaction import (
    AlgodOnComplete,
    AnyTransaction,
    IndexerOnComplete,
    TransactionType,
)
from .utils import encode_address, logger

ALGORAND_ZERO_ADDRESS = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ"


def algod_on_complete_to_indexer_on_complete(
    algod_oc: int,
) -> IndexerOnComplete:
    if algod_oc == AlgodOnComplete.NoOpOC:
        return IndexerOnComplete.noop
    if algod_oc == AlgodOnComplete.OptInOC:
        return IndexerOnComplete.optin
    if algod_oc == AlgodOnComplete.CloseOutOC:
        return IndexerOnComplete.closeout
    if algod_oc == AlgodOnComplete.ClearStateOC:
        return IndexerOnComplete.clear
    if algod_oc == AlgodOnComplete.UpdateApplicationOC:
        return IndexerOnComplete.update
    if algod_oc == AlgodOnComplete.DeleteApplicationOC:
        return IndexerOnComplete.delete

    raise ValueError(f"Unknown on-completion type: {algod_oc}")


def remove_nulls(obj: dict) -> dict:
    for key in list(obj.keys()):
        if obj[key] is None:
            del obj[key]
        elif isinstance(obj[key], dict):
            remove_nulls(obj[key])
    return obj


# /**
#  * Processes a block and returns all transactions from it, including inner transactions, with key information populated.
#  * @param block An Algorand block
#  * @returns An array of processed transactions from the block
#  */
# export function getBlockTransactions(block: Block): TransactionInBlock[] {
#   let offset = 0
#   const getOffset = () => offset++


#   return (block.txns ?? []).flatMap((blockTransaction, roundIndex) => {
#     let parentOffset = 0
#     const getParentOffset = () => parentOffset++
#     const parentData = extractTransactionFromBlockTransaction(blockTransaction, Buffer.from(block.gh), block.gen)
#     return [
#       {
#         blockTransaction,
#         block,
#         roundOffset: getOffset(),
#         roundIndex,
#         roundNumber: block.rnd,
#         roundTimestamp: block.ts,
#         genesisId: block.gen,
#         genesisHash: Buffer.from(block.gh),
#         ...parentData,
#       } as TransactionInBlock,
#       ...(blockTransaction.dt?.itx ?? []).flatMap((innerTransaction) =>
#         getBlockInnerTransactions(
#           innerTransaction,
#           block,
#           blockTransaction,
#           parentData.transaction.txID(),
#           roundIndex,
#           getOffset,
#           getParentOffset,
#         ),
#       ),
#     ]
#   })
# }
def get_block_transactions(block: Block) -> list[TransactionInBlock]:
    txns: list[TransactionInBlock] = []

    offset = 0

    def get_offset() -> int:
        nonlocal offset
        offset += 1
        return offset - 1

    block_txns = block.get("txns")
    if block_txns is None:
        return txns

    for round_index, block_transaction in enumerate(block_txns, start=0):
        parent_offset = 0

        def get_parent_offset() -> int:
            nonlocal parent_offset
            parent_offset += 1
            return parent_offset - 1

        parent_data = extract_transaction_from_block_transaction(
            block_transaction, block["gh"], block["gen"]
        )

        txns.append(
            TransactionInBlock(
                block_transaction=block_transaction,
                round_offset=get_offset(),
                round_index=round_index,
                round_number=block["rnd"],
                round_timestamp=block["ts"],
                genesis_id=block["gen"],
                genesis_hash=block["gh"],
                parent_offset=None,
                parent_transaction_id=None,
                **parent_data,
            )
        )

        if (
            block_transaction.get("dt") is None
            or block_transaction["dt"].get("itx") is None  # type: ignore[union-attr]
        ):
            continue

        for itxn in block_transaction["dt"]["itx"]:  # type: ignore[index]
            txns.extend(
                get_block_inner_transactions(
                    itxn,
                    block,
                    block_transaction,
                    parent_data["transaction"].get_txid(),  # type: ignore[no-untyped-call]
                    round_index,
                    get_offset,
                    get_parent_offset,
                )
            )

    return txns


# function getBlockInnerTransactions(
#   blockTransaction: BlockInnerTransaction,
#   block: Block,
#   parentTransaction: BlockTransaction,
#   parentTransactionId: string,
#   roundIndex: number,
#   getRoundOffset: () => number,
#   getParentOffset: () => number,
# ): TransactionInBlock[] {
#   return [
#     {
#       blockTransaction,
#       roundIndex,
#       roundNumber: block.rnd,
#       roundTimestamp: block.ts,
#       genesisId: block.gen,
#       genesisHash: Buffer.from(block.gh),
#       roundOffset: getRoundOffset(),
#       parentOffset: getParentOffset(),
#       parentTransactionId,
#       ...extractTransactionFromBlockTransaction(blockTransaction, Buffer.from(block.gh), block.gen),
#     },
#     ...(blockTransaction.dt?.itx ?? []).flatMap((innerInnerTransaction) =>
#       getBlockInnerTransactions(
#         innerInnerTransaction,
#         block,
#         parentTransaction,
#         parentTransactionId,
#         roundIndex,
#         getRoundOffset,
#         getParentOffset,
#       ),
#     ),
#   ]
# }
def get_block_inner_transactions(  # noqa: PLR0913
    block_transaction: BlockInnerTransaction,
    block: Block,
    parent_transaction: BlockTransaction,
    parent_transaction_id: str,
    round_index: int,
    get_round_offset: Callable,
    get_parent_offset: Callable,
) -> list[TransactionInBlock]:
    txns = [
        TransactionInBlock(
            block_transaction=block_transaction,
            round_index=round_index,
            round_number=block["rnd"],
            round_timestamp=block["ts"],
            genesis_id=block["gen"],
            genesis_hash=block["gh"],
            round_offset=get_round_offset(),
            parent_offset=get_parent_offset(),
            parent_transaction_id=parent_transaction_id,
            **extract_transaction_from_block_transaction(
                block_transaction, block["gh"], block["gen"]
            ),
        )
    ]

    if block_transaction.get("dt") is None or block_transaction["dt"].get("itx") is None:  # type: ignore[union-attr]
        return txns

    for inner_inner_transaction in block_transaction["dt"]["itx"]:  # type: ignore[index]
        txns.extend(
            get_block_inner_transactions(
                inner_inner_transaction,
                block,
                parent_transaction,
                parent_transaction_id,
                round_index,
                get_round_offset,
                get_parent_offset,
            )
        )

    return txns


class ExtractedBlockTransaction(TypedDict):
    transaction: AnyTransaction
    created_asset_id: int | None
    created_app_id: int | None
    asset_close_amount: int | None
    close_amount: int | None
    logs: list[str] | None


def extract_transaction_from_block_transaction(
    block_transaction: BlockInnerTransaction, genesis_hash: bytes, genesis_id: str
) -> ExtractedBlockTransaction:
    """
    Transform a raw block transaction representation into a `algosdk.Transaction` object and other key transaction data.

    Note: Doesn't currently support `keyreg` (Key Registration) or `stpf` (State Proof) transactions.

    :param block_transaction: The raw transaction from a block
    :type block_transaction: BlockInnerTransaction
    :param genesis_hash: The genesis hash
    :type genesis_hash: bytes
    :param genesis_id: The genesis ID
    :type genesis_id: str
    :return: The `algosdk.Transaction` object along with key secondary information from the block.
    :rtype: ExtractedBlockTransaction
    """
    txn = extract_and_normalise_transaction(block_transaction, genesis_hash, genesis_id)

    # There's a bug in the SDK when decoding app args, so we remove them an add them back manually
    app_args: list[bytes] | None = None
    if "apaa" in txn:
        app_args = txn["apaa"]
        del txn["apaa"]

    t: AnyTransaction = Transaction.undictify(txn)  # type: ignore[no-untyped-call]

    if app_args and isinstance(t, ApplicationCallTxn):
        t.app_args = app_args

    result: ExtractedBlockTransaction = {
        "transaction": t,
        "created_asset_id": block_transaction.get("caid"),
        "created_app_id": block_transaction.get("apid"),
        "asset_close_amount": block_transaction.get("aca"),
        "close_amount": block_transaction.get("ca"),
        "logs": None,
    }

    dt = block_transaction.get("dt")
    if dt is not None and dt.get("lg") is not None:
        result["logs"] = dt["lg"]

    return result


def extract_and_normalise_transaction(
    block_transaction: BlockInnerTransaction | BlockTransaction,
    genesis_hash: bytes,
    genesis_id: str,
) -> dict[str, Any]:
    """
    Extract and normalize a transaction from a block transaction.

    :param block_transaction: The raw transaction from a block
    :type block_transaction: BlockTransaction
    :param genesis_hash: The genesis hash
    :type genesis_hash: bytes
    :param genesis_id: The genesis ID
    :type genesis_id: str
    :return: The normalized transaction
    :rtype: dict[str, Any]
    """
    txn: dict[str, Any] = block_transaction["txn"].copy()
    remove_nulls(txn)

    if block_transaction.get("hgi") is True:
        txn["gen"] = genesis_id

    if block_transaction.get("hgh") is None:
        txn["gh"] = genesis_hash

    if txn["type"] == TransactionType.axfer and txn.get("arcv") is None:
        txn["arcv"] = ALGORAND_ZERO_ADDRESS

    if txn["type"] == TransactionType.pay and txn.get("rcv") is None:
        txn["rcv"] = ALGORAND_ZERO_ADDRESS

    return txn


# Taken from algosdk
def _sort_dict(d: dict) -> OrderedDict:
    """
    Sorts a dictionary recursively and removes all zero values.

    :param d: dictionary to be sorted
    :type d: dict
    :return: sorted dictionary with no zero values
    :rtype: OrderedDict
    """
    od = OrderedDict()
    for k, v in sorted(d.items()):
        if isinstance(v, dict):
            od[k] = _sort_dict(v)
        elif v:
            od[k] = v
    return od


def get_tx_id_from_block_transaction(
    block_transaction: BlockTransaction | BlockInnerTransaction,
    genesis_hash: bytes,
    genesis_id: str,
) -> str:
    """
    Get the transaction ID from a block transaction.

    :param block_transaction: The block transaction
    :type block_transaction: BlockTransaction | BlockInnerTransaction
    :param genesis_hash: The genesis hash
    :type genesis_hash: bytes
    :param genesis_id: The genesis ID
    :type genesis_id: str
    :return: The transaction ID
    :rtype: str
    """
    txn = extract_and_normalise_transaction(block_transaction, genesis_hash, genesis_id)

    algorand_transaction_length = 52
    encoded_message = msgpack.packb(_sort_dict(txn), use_bin_type=True)
    tag = b"TX"
    gh = tag + encoded_message
    raw_tx_id = hashlib.new("sha512_256", gh).digest()
    return base64.b32encode(raw_tx_id).decode()[:algorand_transaction_length]


class TransactionInBlockWithChildOffset(TransactionInBlock):
    get_child_offset: NotRequired[Callable[[], int]]


def convert_bytes_to_base64(obj: Any) -> Any:  # noqa: ANN401
    """
    Recursively iterate over a nested dict and convert any bytes values to base64 strings.

    :param obj: The object to convert (can be a dict, list, or any other type)
    :type obj: Any
    :return: The object with all bytes values converted to base64 strings
    :rtype: Any
    """
    if isinstance(obj, dict):
        return {key: convert_bytes_to_base64(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_bytes_to_base64(item) for item in obj]
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode("utf-8")
    else:
        return obj


def get_indexer_transaction_from_algod_transaction(  # noqa: C901
    t: TransactionInBlock | TransactionInBlockWithChildOffset,
    filter_name: str | None = None,
) -> SubscribedTransaction:
    transaction = t["transaction"]
    created_asset_id = t["created_asset_id"]
    block_transaction = t["block_transaction"]
    asset_close_amount = t["asset_close_amount"]
    close_amount = t.get("close_amount")
    created_app_id = t.get("created_app_id")
    round_offset = t["round_offset"]
    parent_offset = t["parent_offset"] or 0
    parent_transaction_id = t.get("parent_transaction_id")
    round_index = t["round_index"]
    round_number = t["round_number"]
    round_timestamp = t["round_timestamp"]
    genesis_hash = t["genesis_hash"]
    genesis_id = t["genesis_id"]

    if not transaction.type:
        raise ValueError(
            f"Received no transaction type for transaction {transaction.get_txid()}"  # type: ignore[no-untyped-call]
        )

    child_offset = round_offset

    def get_child_offset() -> int:
        return child_offset + 1

    if "get_child_offset" in t:
        get_child_offset = cast(TransactionInBlockWithChildOffset, t)[
            "get_child_offset"
        ]

    tx_id = (
        transaction.get_txid()  # type: ignore[no-untyped-call]
        if transaction.type != "stpf"
        else get_tx_id_from_block_transaction(
            block_transaction, genesis_hash, genesis_id
        )
    )

    try:
        raw_logs = list((block_transaction.get("dt") or {"lg": []}).get("lg", []))
        bytes_logs = [
            raw_log.encode("utf-8", errors="surrogateescape") for raw_log in raw_logs
        ]
        b64_logs = [base64.b64encode(log).decode("utf-8") for log in bytes_logs]

        result: SubscribedTransaction = {
            "id": (
                f"{parent_transaction_id}/inner/{parent_offset + 1}"
                if parent_transaction_id
                else tx_id
            ),
            "parent_transaction_id": parent_transaction_id,
            "filters_matched": [str(filter_name)] if filter_name else [],
            "first-valid": transaction.first_valid_round,
            "last-valid": transaction.last_valid_round,
            "tx-type": transaction.type,
            "fee": transaction.fee,
            "sender": transaction.sender,
            "confirmed-round": round_number,
            "round-time": round_timestamp,
            "intra-round-offset": round_offset,
            "created-asset-index": created_asset_id,
            "genesis-hash": transaction.genesis_hash,
            "genesis-id": transaction.genesis_id,
            "group": (
                base64.b64encode(transaction.group).decode("utf-8")
                if transaction.group
                else None
            ),
            "note": transaction.note or "",
            "lease": transaction.lease or "",
            "rekey-to": transaction.rekey_to,
            "closing-amount": close_amount,
            "created-application-index": created_app_id,
            "auth-addr": (
                encode_address(cast(bytes, block_transaction.get("sgnr")))
                if block_transaction.get("sgnr")
                else None
            ),
            "logs": b64_logs if len(b64_logs) > 0 else None,
        }

        if isinstance(transaction, AssetConfigTxn):
            result["asset-config-transaction"] = {
                "asset-id": transaction.index,
                "params": block_transaction["txn"].get("apar", {}),
            }
        elif isinstance(transaction, AssetTransferTxn):
            result["asset-transfer-transaction"] = {
                "asset-id": transaction.index,
                "amount": transaction.amount,
                "receiver": transaction.receiver,
                "sender": (
                    (transaction.revocation_target)
                    if transaction.revocation_target
                    else None
                ),
                "close-amount": asset_close_amount,
                "close-to": (
                    (transaction.close_assets_to)
                    if transaction.close_assets_to
                    else None
                ),
            }
        elif isinstance(transaction, AssetFreezeTxn):
            result["asset-freeze-transaction"] = {
                "asset-id": transaction.index,
                "new-freeze-status": transaction.new_freeze_state,
                "address": transaction.target,
            }
        elif isinstance(transaction, ApplicationCallTxn):
            result["application-transaction"] = {
                "application-id": transaction.index,
                "approval-program": transaction.approval_program or "",
                "clear-state-program": transaction.clear_program or "",
                "on-completion": algod_on_complete_to_indexer_on_complete(
                    transaction.on_complete
                ).value,
                "application-args": [
                    base64.b64encode(b).decode("utf-8")
                    for b in transaction.app_args or []
                ],
                "extra-program-pages": transaction.extra_pages or None,
                "foreign-apps": transaction.foreign_apps,
                "foreign-assets": transaction.foreign_assets,
                "accounts": transaction.accounts,
            }
        elif isinstance(transaction, PaymentTxn):
            result["payment-transaction"] = {
                "amount": transaction.amt,
                "receiver": transaction.receiver,
                "close-amount": close_amount,
                "close-remainder-to": (
                    transaction.close_remainder_to
                    if transaction.close_remainder_to
                    else None
                ),
            }
        # elif transaction.type == "keyreg":
        elif isinstance(transaction, KeyregTxn):
            result["keyreg-transaction"] = {
                "non-participation": transaction.nonpart,
                "selection-participation-key": transaction.selkey,
                "state-proof-key": transaction.sprfkey,
                "vote-first-valid": transaction.votefst,
                "vote-key-dilution": transaction.votekd,
                "vote-last-valid": transaction.votelst,
                "vote-participation-key": transaction.votepk,
            }
        # elif transaction.type == "stpf":
        elif isinstance(transaction, StateProofTxn):
            state_proof = transaction.sprf
            state_proof_message = transaction.sprfmsg
            result["state-proof-transaction"] = {
                "state-proof": {
                    "part-proofs": {
                        "hash-factory": {"hash-type": state_proof["P"]["hsh"]["t"]},
                        "tree-depth": state_proof["P"]["td"],
                        "path": list(state_proof["P"]["pth"]),
                    },
                    "positions-to-reveal": state_proof["pr"],
                    "salt-version": state_proof.get("v", 0),
                    "sig-commit": state_proof["c"],
                    "sig-proofs": {
                        "hash-factory": {"hash-type": state_proof["S"]["hsh"]["t"]},
                        "tree-depth": state_proof["S"]["td"],
                        "path": list(state_proof["S"]["pth"]),
                    },
                    "signed-weight": state_proof["w"],
                    "reveals": [
                        {
                            "sig-slot": {
                                "lower-sig-weight": state_proof["r"][position]["s"].get(
                                    "l", 0
                                ),
                                "signature": {
                                    "merkle-array-index": state_proof["r"][position][
                                        "s"
                                    ]["s"]["idx"],
                                    "falcon-signature": state_proof["r"][position]["s"][
                                        "s"
                                    ]["sig"],
                                    "proof": {
                                        "hash-factory": {
                                            "hash-type": state_proof["r"][position][
                                                "s"
                                            ]["s"]["prf"]["hsh"]["t"]
                                        },
                                        "tree-depth": state_proof["r"][position]["s"][
                                            "s"
                                        ]["prf"]["td"],
                                        "path": list(
                                            state_proof["r"][position]["s"]["s"]["prf"][
                                                "pth"
                                            ]
                                        ),
                                    },
                                    "verifying-key": state_proof["r"][position]["s"][
                                        "s"
                                    ]["vkey"]["k"],
                                },
                            },
                            "position": position,
                            "participant": {
                                "weight": state_proof["r"][position]["p"]["w"],
                                "verifier": {
                                    "key-lifetime": state_proof["r"][position]["p"][
                                        "p"
                                    ]["lf"],
                                    "commitment": state_proof["r"][position]["p"]["p"][
                                        "cmt"
                                    ],
                                },
                            },
                        }
                        for position in state_proof["r"]
                    ],
                },
                "message": {
                    "block-headers-commitment": state_proof_message["b"],
                    "first-attested-round": state_proof_message["f"],
                    "latest-attested-round": state_proof_message["l"],
                    "ln-proven-weight": state_proof_message["P"],
                    "voters-commitment": state_proof_message["v"],
                },
                "state-proof-type": transaction.sprf_type or 0,
            }

        if block_transaction.get("dt") is not None:
            result["inner-txns"] = [
                get_indexer_transaction_from_algod_transaction(
                    {
                        "block_transaction": ibt,
                        "round_index": round_index,
                        "round_offset": get_child_offset(),
                        **extract_transaction_from_block_transaction(
                            ibt, genesis_hash, genesis_id
                        ),
                        "parent_offset": parent_offset,
                        "parent_transaction_id": parent_transaction_id,
                        "round_number": round_number,
                        "round_timestamp": round_timestamp,
                        "genesis_hash": genesis_hash,
                        "genesis_id": genesis_id,
                        "get_child_offset": get_child_offset,
                    }
                )
                for ibt in block_transaction["dt"].get("itx", [])  # type: ignore[union-attr]
            ]

        return cast(SubscribedTransaction, convert_bytes_to_base64(result))

    except Exception as e:
        logger.error(
            f"Failed to transform transaction {tx_id} from block {round_number} with offset {round_offset}"
        )
        raise e


def block_data_to_block_metadata(block_data: BlockData) -> BlockMetadata:
    """
    Extract key metadata from a block.

    :param block_data: The raw block data
    :type block_data: BlockData
    :return: The block metadata
    :rtype: BlockMetadata
    """
    block = block_data["block"]
    cert = block_data.get("cert")

    return {
        "round": block["rnd"],
        "hash": (
            base64.b64encode(cert["prop"]["dig"]).decode("utf-8")
            if cert and cert.get("prop", {}).get("dig")
            else None
        ),
        "timestamp": block["ts"],
        "genesis_id": block["gen"],
        "genesis_hash": base64.b64encode(block["gh"]).decode("utf-8"),
        "previous_block_hash": (
            base64.b64encode(block["prev"]).decode("utf-8") if block["prev"] else None
        ),
        "seed": base64.b64encode(block["seed"]).decode("utf-8"),
        "parent_transaction_count": len(block.get("txns") or []),
        "full_transaction_count": count_all_transactions(block.get("txns") or []),
        "rewards": {
            "fee_sink": encode_address(block["fees"]),
            "rewards_pool": encode_address(block["rwd"]),
            "rewards_level": block.get("earn", 0),
            "rewards_residue": block.get("frac", 0),
            "rewards_rate": block.get("rate") or 0,
            "rewards_calculation_round": block["rwcalr"],
        },
        "upgrade_state": {
            "current_protocol": block["proto"],
            "next_protocol": block.get("nextproto"),
            "next_protocol_approvals": block.get("nextyes"),
            "next_protocol_switch_on": block.get("nextswitch"),
            "next_protocol_vote_before": block.get("nextbefore"),
        },
        "txn_counter": block.get("tc", 0),
        "transactions_root": base64.b64encode(block.get("txn", b"")).decode("utf-8"),
        "transactions_root_sha256": block.get("txn256", ""),
    }


def count_all_transactions(
    txns: Sequence[BlockTransaction | BlockInnerTransaction],
) -> int:
    return sum(
        1 + count_all_transactions(getattr(txn.get("dt", {}), "itx", []))
        for txn in txns
    )


def extract_balance_changes_from_block_transaction(  # noqa: PLR0912, C901
    transaction: BlockTransaction | BlockInnerTransaction,
) -> list[BalanceChange]:
    balance_changes: list[BalanceChange] = []

    if (transaction.get("txn", {}).get("fee", 0)) > 0:
        balance_changes.append(
            {
                "address": encode_address(transaction["txn"]["snd"]),
                "amount": -1 * (transaction["txn"].get("fee", 0) or 0),
                "roles": [BalanceChangeRole.Sender],
                "asset_id": 0,
            }
        )

    if transaction["txn"].get("type") == TransactionType.pay.value:
        balance_changes.extend(
            [
                {
                    "address": encode_address(transaction["txn"]["snd"]),
                    "amount": -1 * (transaction["txn"].get("amt", 0) or 0),
                    "roles": [BalanceChangeRole.Sender],
                    "asset_id": 0,
                }
            ]
        )

        if transaction["txn"].get("rcv"):
            balance_changes.append(
                {
                    "address": encode_address(transaction["txn"]["rcv"]),
                    "amount": transaction["txn"].get("amt", 0) or 0,
                    "roles": [BalanceChangeRole.Receiver],
                    "asset_id": 0,
                }
            )

        if transaction.get("ca") and transaction["txn"].get("close"):
            balance_changes.extend(
                [
                    {
                        "address": encode_address(transaction["txn"]["close"]),
                        "amount": transaction.get("ca", 0) or 0,
                        "roles": [BalanceChangeRole.CloseTo],
                        "asset_id": 0,
                    },
                    {
                        "address": encode_address(transaction["txn"]["snd"]),
                        "amount": -1 * (transaction.get("ca", 0) or 0),
                        "roles": [BalanceChangeRole.Sender],
                        "asset_id": 0,
                    },
                ]
            )

    if transaction["txn"].get("type") == TransactionType.axfer.value and transaction[
        "txn"
    ].get("xaid"):
        balance_changes.append(
            {
                "address": encode_address(
                    transaction["txn"].get("asnd", transaction["txn"]["snd"])
                ),
                "asset_id": transaction["txn"]["xaid"],
                "amount": -1 * (transaction["txn"].get("aamt", 0) or 0),
                "roles": [BalanceChangeRole.Sender],
            }
        )

        if transaction["txn"].get("arcv"):
            balance_changes.append(
                {
                    "address": encode_address(transaction["txn"]["arcv"]),
                    "asset_id": transaction["txn"]["xaid"],
                    "amount": transaction["txn"].get("aamt", 0) or 0,
                    "roles": [BalanceChangeRole.Receiver],
                }
            )

        if transaction.get("aca") and transaction["txn"].get("aclose"):
            balance_changes.extend(
                [
                    {
                        "address": encode_address(transaction["txn"]["aclose"]),
                        "asset_id": transaction["txn"]["xaid"],
                        "amount": transaction.get("aca", 0) or 0,
                        "roles": [BalanceChangeRole.CloseTo],
                    },
                    {
                        "address": encode_address(
                            transaction["txn"].get("asnd", transaction["txn"]["snd"])
                        ),
                        "asset_id": transaction["txn"]["xaid"],
                        "amount": -1 * (transaction.get("aca", 0) or 0),
                        "roles": [BalanceChangeRole.Sender],
                    },
                ]
            )

    if transaction["txn"].get("type") == TransactionType.acfg.value:
        if not transaction["txn"].get("caid") and transaction.get("caid"):
            balance_changes.append(
                {
                    "address": encode_address(transaction["txn"]["snd"]),
                    "asset_id": transaction["caid"] or 0,
                    "amount": transaction["txn"].get("apar", {}).get("t", 0) or 0,
                    "roles": [BalanceChangeRole.AssetCreator],
                }
            )
        elif transaction["txn"].get("caid") and not transaction["txn"].get("apar"):
            balance_changes.append(
                {
                    "address": encode_address(transaction["txn"]["snd"]),
                    "asset_id": transaction["txn"]["caid"],
                    "amount": 0,
                    "roles": [BalanceChangeRole.AssetDestroyer],
                }
            )

    # Consolidate balance changes
    consolidated_changes: dict[tuple[str, int], Any] = {}
    for change in balance_changes:
        key = (change["address"], change["asset_id"])
        if key in consolidated_changes:
            consolidated_changes[key]["amount"] += change["amount"]
            consolidated_changes[key]["roles"] = list(
                set(consolidated_changes[key]["roles"] + change["roles"])
            )
        else:
            consolidated_changes[key] = change

    return list(consolidated_changes.values())


def extract_balance_changes_from_indexer_transaction(  # noqa: C901
    transaction: TransactionResult,
) -> list[BalanceChange]:
    balance_changes: list[BalanceChange] = []

    if transaction.get("fee", 0) > 0:
        balance_changes.append(
            BalanceChange(
                address=transaction["sender"],
                amount=-1 * int(transaction["fee"]),
                roles=[BalanceChangeRole.Sender],
                asset_id=0,
            )
        )

    if (
        transaction["tx-type"] == TransactionType.pay.value
        and "payment-transaction" in transaction
    ):
        pay = transaction["payment-transaction"]
        balance_changes.extend(
            [
                BalanceChange(
                    address=transaction["sender"],
                    amount=-1 * (pay.get("amount") or 0),
                    roles=[BalanceChangeRole.Sender],
                    asset_id=0,
                ),
                BalanceChange(
                    address=pay["receiver"],
                    amount=pay["amount"],
                    roles=[BalanceChangeRole.Receiver],
                    asset_id=0,
                ),
            ]
        )

        if "close-amount" in pay:
            balance_changes.extend(
                [
                    BalanceChange(
                        address=str(["close-remainder-to"]),
                        amount=pay.get("close-amount") or 0,
                        roles=[BalanceChangeRole.CloseTo],
                        asset_id=0,
                    ),
                    BalanceChange(
                        address=transaction["sender"],
                        amount=-1 * (pay.get("close-amount") or 0),
                        roles=[BalanceChangeRole.Sender],
                        asset_id=0,
                    ),
                ]
            )

    if (
        transaction["tx-type"] == TransactionType.axfer.value
        and "asset-transfer-transaction" in transaction
    ):
        axfer = transaction["asset-transfer-transaction"]
        balance_changes.extend(
            [
                BalanceChange(
                    address=axfer.get("sender") or transaction["sender"],
                    asset_id=axfer["asset-id"],
                    amount=-1 * (axfer.get("amount") or 0),
                    roles=[BalanceChangeRole.Sender],
                ),
                BalanceChange(
                    address=axfer["receiver"],
                    asset_id=axfer["asset-id"],
                    amount=axfer.get("amount", 0),
                    roles=[BalanceChangeRole.Receiver],
                ),
            ]
        )

        if axfer.get("close-amount") is not None and axfer.get("close-to") is not None:
            balance_changes.extend(
                [
                    BalanceChange(
                        address=str(axfer["close-to"]),
                        asset_id=axfer["asset-id"],
                        amount=axfer.get("close-amount") or 0,
                        roles=[BalanceChangeRole.CloseTo],
                    ),
                    BalanceChange(
                        address=axfer.get("sender") or transaction["sender"],
                        asset_id=axfer["asset-id"],
                        amount=-1 * (axfer.get("close-amount") or 0),
                        roles=[BalanceChangeRole.Sender],
                    ),
                ]
            )

    if (
        transaction["tx-type"] == TransactionType.acfg.value
        and "asset-config-transaction" in transaction
    ):
        acfg = transaction["asset-config-transaction"]
        if (
            acfg.get("asset-id") is None
            and transaction.get("created-asset-index") is not None
        ):
            balance_changes.append(
                BalanceChange(
                    address=transaction["sender"],
                    asset_id=transaction["created-asset-index"] or 0,
                    amount=int(acfg.get("params", {}).get("total", 0)),
                    roles=[BalanceChangeRole.AssetCreator],
                )
            )
        elif "asset-id" in acfg and "params" not in acfg:
            balance_changes.append(
                BalanceChange(
                    address=transaction["sender"],
                    asset_id=acfg["asset-id"],
                    amount=0,
                    roles=[BalanceChangeRole.AssetDestroyer],
                )
            )

    # Consolidate balance changes
    consolidated_changes: dict[tuple, BalanceChange] = {}
    for change in balance_changes:
        key = (change["address"], change["asset_id"])
        if key in consolidated_changes:
            existing = consolidated_changes[key]
            existing["amount"] += change["amount"]
            existing["roles"].extend(
                [role for role in change["roles"] if role not in existing["roles"]]
            )
        else:
            consolidated_changes[key] = change

    return list(consolidated_changes.values())
