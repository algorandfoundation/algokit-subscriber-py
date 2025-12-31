import base64
import dataclasses
import itertools
import logging
import typing
from collections.abc import Iterator, Sequence

from algokit_algod_client import models as algod
from algokit_indexer_client import models as indexer
from algokit_transact import (
    AssetConfigTransactionFields,
    LogicSigSignature,
    MultisigSignature,
    MultisigSubsignature,
    OnApplicationComplete,
    PaymentTransactionFields,
    StateSchema,
    TransactionType,
)
from algokit_transact import (
    Transaction as AlgodTransaction,
)
from algokit_transact.models import app_call
from algokit_transact.models import state_proof as sp_models

from .types.subscription import (
    BlockMetadata,
    BlockRewards,
    BlockUpgradeState,
)

logger = logging.getLogger(__package__)
ALGORAND_ZERO_ADDRESS = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ"


_ON_COMPLETE = {
    OnApplicationComplete.NoOp: indexer.OnCompletion.NOOP,
    OnApplicationComplete.OptIn: indexer.OnCompletion.OPTIN,
    OnApplicationComplete.CloseOut: indexer.OnCompletion.CLOSEOUT,
    OnApplicationComplete.ClearState: indexer.OnCompletion.CLEAR,
    OnApplicationComplete.UpdateApplication: indexer.OnCompletion.UPDATE,
    OnApplicationComplete.DeleteApplication: indexer.OnCompletion.DELETE,
}


def get_block_transactions(block: algod.Block) -> list[indexer.Transaction]:
    intra_round_offset = itertools.count()
    txns = [
        _get_indexer_transaction_from_algod_transaction(
            block,
            _get_normalized_txn(block.header, txn),
            intra_round_offset_iter=intra_round_offset,
        )
        for offset, txn in enumerate(block.payset or [])
    ]

    if block.header.proposer_payout and block.header.proposer:
        payout_txn = _get_synthetic_block_payout_transaction(
            block,
            intra_round_offset,
        )
        txns.append(payout_txn)

    return txns


def _get_indexer_transaction_from_algod_transaction(
    block: algod.Block,
    signed_txn_with_ad: algod.SignedTxnWithAD,
    *,
    intra_round_offset_iter: Iterator[int],
    parent: algod.SignedTxnWithAD | None = None,
) -> indexer.Transaction:
    # Extract from nested structure
    apply_data = signed_txn_with_ad.apply_data
    signed_txn = signed_txn_with_ad.signed_transaction
    header = block.header
    transaction = signed_txn_with_ad.signed_transaction.txn

    logs = None
    if apply_data and apply_data.eval_delta and apply_data.eval_delta.logs:
        logs = apply_data.eval_delta.logs

    try:
        # Handle inner transactions
        inner_txns = list[indexer.Transaction]()
        eval_delta = apply_data.eval_delta if apply_data else None
        intra_round_offset = next(intra_round_offset_iter)
        account_references = [transaction.sender]
        if transaction.application_call:
            account_references.extend(transaction.application_call.account_references or [])
        if eval_delta:
            if eval_delta.inner_txns:
                for itxn in eval_delta.inner_txns:
                    inner_txns.append(
                        _get_indexer_transaction_from_algod_transaction(
                            block,
                            itxn,
                            intra_round_offset_iter=intra_round_offset_iter,
                            parent=signed_txn_with_ad,
                        )
                    )
            if eval_delta.shared_accounts:
                account_references.extend(eval_delta.shared_accounts)
        return indexer.Transaction(
            id_=transaction.tx_id() if parent is None else None,
            fee=transaction.fee or 0,
            first_valid=transaction.first_valid,
            last_valid=transaction.last_valid,
            sender=transaction.sender,
            tx_type=transaction.transaction_type.value,
            confirmed_round=header.round,
            round_time=header.timestamp,
            intra_round_offset=intra_round_offset,
            genesis_hash=transaction.genesis_hash,
            genesis_id=transaction.genesis_id,
            created_asset_id=apply_data.config_asset if apply_data else None,
            created_app_id=apply_data.application_id if apply_data else None,
            close_rewards=(apply_data.close_rewards or 0) if apply_data else 0,
            closing_amount=(apply_data.closing_amount or 0) if apply_data else 0,
            receiver_rewards=(apply_data.receiver_rewards or 0) if apply_data else 0,
            sender_rewards=(apply_data.sender_rewards or 0) if apply_data else 0,
            global_state_delta=_convert_global_state_delta(eval_delta),
            local_state_delta=_convert_local_state_delta(eval_delta, account_references),
            logs=logs,
            auth_addr=signed_txn.auth_address,
            note=transaction.note,
            lease=transaction.lease,
            rekey_to=transaction.rekey_to,
            group=transaction.group,
            inner_txns=inner_txns,
            payment_transaction=_convert_pay_transaction(signed_txn_with_ad),
            asset_config_transaction=_convert_asset_config_transaction(signed_txn_with_ad),
            asset_transfer_transaction=_convert_asset_transfer_transaction(signed_txn_with_ad),
            asset_freeze_transaction=_convert_asset_freeze_transaction(signed_txn_with_ad),
            application_transaction=_convert_application_transaction(signed_txn_with_ad),
            keyreg_transaction=_convert_keyreg_transaction(signed_txn_with_ad),
            state_proof_transaction=_convert_state_proof_transaction(signed_txn_with_ad),
            heartbeat_transaction=_convert_heartbeat_transaction(signed_txn_with_ad),
            signature=_convert_signature(
                signed_txn_with_ad.signed_transaction, transaction.transaction_type
            ),
        )

    except Exception as e:
        logger.error(
            f"Failed to transform transaction from block {header.round}, "
            f"tx_id={transaction.tx_id()}"
        )
        raise e


def _convert_signature(
    signed_txn: algod.SignedTransaction, tx_type: TransactionType
) -> indexer.TransactionSignature | None:
    if (
        not (signed_txn.lsig or signed_txn.msig or signed_txn.sig)
        # indexer returns and empty signature rather than None for state proofs
        and tx_type != TransactionType.StateProof
    ):
        return None
    return indexer.TransactionSignature(
        logicsig=_convert_lsig(signed_txn.lsig) if signed_txn.lsig else None,
        multisig=_convert_msig(signed_txn.msig),
        sig=signed_txn.sig,
    )


def _convert_lsig(lsig: LogicSigSignature) -> indexer.TransactionSignatureLogicsig:
    return indexer.TransactionSignatureLogicsig(
        logic=lsig.logic,
        args=lsig.args,
        signature=lsig.sig,
        logic_multisig_signature=_convert_msig(lsig.lmsig),
        multisig_signature=_convert_msig(lsig.msig),
    )


def _convert_msig(msig: MultisigSignature | None) -> indexer.TransactionSignatureMultisig | None:
    if msig is None:
        return None
    return indexer.TransactionSignatureMultisig(
        subsignature=[_convert_ssig(s) for s in msig.subsigs] or None,
        threshold=msig.threshold,
        version=msig.version,
    )


def _convert_ssig(ssig: MultisigSubsignature) -> indexer.TransactionSignatureMultisigSubsignature:
    return indexer.TransactionSignatureMultisigSubsignature(
        public_key=ssig.public_key, signature=ssig.sig
    )


def _convert_global_state_delta(
    eval_delta: algod.BlockAppEvalDelta | None,
) -> list[indexer.EvalDeltaKeyValue] | None:
    if not eval_delta or eval_delta.global_delta is None:
        return None
    return [_convert_state_delta(key, delta) for key, delta in eval_delta.global_delta.items()]


def _convert_local_state_delta(
    eval_delta: algod.BlockAppEvalDelta | None,
    account_references: list[str],
) -> list[indexer.AccountStateDelta] | None:
    if not eval_delta or eval_delta.local_deltas is None:
        return None
    return [
        indexer.AccountStateDelta(
            address=account_references[account_index],
            delta=[_convert_state_delta(key, delta) for key, delta in deltas.items()],
        )
        for account_index, deltas in eval_delta.local_deltas.items()
    ]


def _convert_state_delta(key: bytes, delta: algod.BlockEvalDelta) -> indexer.EvalDeltaKeyValue:
    return indexer.EvalDeltaKeyValue(
        key=key,
        value=indexer.EvalDelta(
            uint=delta.uint or 0,
            bytes_=delta.bytes_,
            action=delta.action,
        ),
    )


def _get_normalized_txn(
    header: algod.BlockHeader, txn_in_block: algod.SignedTxnInBlock
) -> algod.SignedTxnWithAD:
    signed_txn_with_ad = txn_in_block.signed_transaction
    txn = signed_txn_with_ad.signed_transaction.txn
    changes = dict[str, typing.Any]()
    if txn_in_block.has_genesis_id and txn.genesis_id is None:
        changes["genesis_id"] = header.genesis_id

    if txn_in_block.has_genesis_hash is not False and txn.genesis_hash is None:
        changes["genesis_hash"] = header.genesis_hash

    if changes:
        txn = dataclasses.replace(txn, **changes)
        signed_txn_with_ad = algod.SignedTxnWithAD(
            signed_transaction=dataclasses.replace(signed_txn_with_ad.signed_transaction, txn=txn),
            apply_data=signed_txn_with_ad.apply_data,
        )
    return signed_txn_with_ad


def _convert_pay_transaction(
    txn_with_apply_data: algod.SignedTxnWithAD,
) -> indexer.TransactionPayment | None:
    txn = txn_with_apply_data.signed_transaction.txn
    pay = txn.payment
    if not pay:
        return None
    apply_data = txn_with_apply_data.apply_data
    close_amount = apply_data.closing_amount if apply_data else None
    return indexer.TransactionPayment(
        amount=pay.amount,
        receiver=pay.receiver,
        close_amount=close_amount or 0,
        close_remainder_to=pay.close_remainder_to,
    )


def _has_asset_config(ac: AssetConfigTransactionFields) -> bool:
    return any(
        v is not None
        for v in (
            ac.total,
            ac.decimals,
            ac.default_frozen,
            ac.unit_name,
            ac.asset_name,
            ac.url,
            ac.metadata_hash,
            ac.manager,
            ac.reserve,
            ac.freeze,
            ac.clawback,
        )
    )


def _convert_asset_config_transaction(
    txn_with_apply_data: algod.SignedTxnWithAD,
) -> indexer.TransactionAssetConfig | None:
    txn = txn_with_apply_data.signed_transaction.txn
    ac = txn.asset_config
    if ac is None:
        return None
    params = None
    if _has_asset_config(ac):
        params = indexer.AssetParams(
            creator=txn.sender,
            decimals=ac.decimals or 0,
            total=ac.total or 0,
            clawback=ac.clawback,
            default_frozen=ac.default_frozen or False,
            freeze=ac.freeze,
            manager=ac.manager,
            metadata_hash=ac.metadata_hash,
            name=ac.asset_name,
            name_b64=_convert_utf8_to_bytes(ac.asset_name),
            reserve=ac.reserve,
            unit_name=ac.unit_name,
            unit_name_b64=_convert_utf8_to_bytes(ac.unit_name),
            url=ac.url,
            url_b64=_convert_utf8_to_bytes(ac.url),
        )
    if txn_with_apply_data.apply_data and txn_with_apply_data.apply_data.config_asset:
        asset_id: int | None = 0
    else:
        asset_id = ac.asset_id or None
    return indexer.TransactionAssetConfig(
        asset_id=asset_id,
        params=params,
    )


def _convert_utf8_to_bytes(value: str | None) -> bytes | None:
    return None if value is None else value.encode("utf-8")


def _convert_asset_transfer_transaction(
    txn_with_apply_data: algod.SignedTxnWithAD,
) -> indexer.TransactionAssetTransfer | None:
    txn = txn_with_apply_data.signed_transaction.txn
    at = txn.asset_transfer
    if not at:
        return None
    apply_data = txn_with_apply_data.apply_data
    asset_close_amount = apply_data.asset_closing_amount if apply_data else None
    return indexer.TransactionAssetTransfer(
        asset_id=at.asset_id,
        amount=at.amount,
        receiver=at.receiver,
        close_amount=asset_close_amount or 0,
        close_to=at.close_remainder_to,
        sender=at.asset_sender,
    )


def _convert_asset_freeze_transaction(
    txn_with_apply_data: algod.SignedTxnWithAD,
) -> indexer.TransactionAssetFreeze | None:
    txn = txn_with_apply_data.signed_transaction.txn
    af = txn.asset_freeze
    if not af:
        return None
    return indexer.TransactionAssetFreeze(
        asset_id=af.asset_id,
        address=af.freeze_target,
        new_freeze_status=af.frozen,
    )


def _convert_application_transaction(
    txn_with_apply_data: algod.SignedTxnWithAD,
) -> indexer.TransactionApplication | None:
    txn = txn_with_apply_data.signed_transaction.txn
    app = txn.application_call
    if not app:
        return None
    app_id = app.app_id
    if not app_id and txn_with_apply_data.apply_data:
        app_id = txn_with_apply_data.apply_data.application_id or 0
    return indexer.TransactionApplication(
        application_id=app.app_id,
        on_completion=_ON_COMPLETE[app.on_complete],
        approval_program=app.approval_program,
        clear_state_program=app.clear_state_program,
        application_args=app.args,
        extra_program_pages=app.extra_program_pages,
        foreign_apps=app.app_references or [],
        foreign_assets=app.asset_references or [],
        accounts=app.account_references or [],
        global_state_schema=_convert_schema(app.global_state_schema),
        local_state_schema=_convert_schema(app.local_state_schema),
        box_references=[_convert_box_ref(app_id, ref) for ref in app.box_references or []] or None,
        access=[_convert_access_ref(app_id, ref) for ref in app.access_references or []] or None,
        reject_version=app.reject_version,
    )


def _convert_schema(schema: StateSchema | None) -> indexer.StateSchema:
    return indexer.StateSchema(
        num_byte_slices=schema.num_byte_slices if schema else 0,
        num_uints=schema.num_uints if schema else 0,
    )


def _convert_box_ref(app_id: int, ref: app_call.BoxReference) -> indexer.BoxReference:
    if app_id == ref.app_id or not ref.name:
        app_id = 0
    else:
        app_id = ref.app_id
    name = ref.name or None
    return indexer.BoxReference(
        app=app_id,
        # TODO: resolve why indexer returns None here instead of b""
        name=name,  # type: ignore[arg-type]
    )


def _convert_access_ref(app_id: int, ref: app_call.ResourceReference) -> indexer.ResourceRef:
    return indexer.ResourceRef(
        address=ref.address,
        application_id=ref.app_id,
        asset_id=ref.asset_id,
        box=_convert_box_ref(app_id, ref.box) if ref.box else None,
        holding=indexer.HoldingRef(address=ref.holding.address, asset=ref.holding.asset_id)
        if ref.holding
        else None,
        local=indexer.LocalsRef(address=ref.locals.address, app=ref.locals.app_id)
        if ref.locals
        else None,
    )


def _convert_keyreg_transaction(
    txn_with_apply_data: algod.SignedTxnWithAD,
) -> indexer.TransactionKeyreg | None:
    txn = txn_with_apply_data.signed_transaction.txn
    kr = txn.key_registration
    if not kr:
        return None
    return indexer.TransactionKeyreg(
        non_participation=kr.non_participation or False,
        selection_participation_key=kr.selection_key,
        state_proof_key=kr.state_proof_key,
        vote_first_valid=kr.vote_first,
        vote_key_dilution=kr.vote_key_dilution,
        vote_last_valid=kr.vote_last,
        vote_participation_key=kr.vote_key,
    )


def _convert_state_proof_transaction(
    txn_with_apply_data: algod.SignedTxnWithAD,
) -> indexer.TransactionStateProof | None:
    txn = txn_with_apply_data.signed_transaction.txn
    state_proof_fields = txn.state_proof
    if not state_proof_fields:
        return None

    state_proof = state_proof_fields.state_proof
    state_proof_message = state_proof_fields.message

    return indexer.TransactionStateProof(
        state_proof=_convert_state_proof(state_proof) if state_proof else None,
        message=(
            indexer.IndexerStateProofMessage(
                block_headers_commitment=state_proof_message.block_headers_commitment,
                voters_commitment=state_proof_message.voters_commitment,
                ln_proven_weight=state_proof_message.ln_proven_weight,
                first_attested_round=state_proof_message.first_attested_round,
                latest_attested_round=state_proof_message.last_attested_round,
            )
            if state_proof_message
            else None
        ),
        state_proof_type=state_proof_fields.state_proof_type or 0,
    )


def _convert_heartbeat_transaction(
    txn_with_apply_data: algod.SignedTxnWithAD,
) -> indexer.TransactionHeartbeat | None:
    txn = txn_with_apply_data.signed_transaction.txn
    heartbeat = txn.heartbeat
    if not heartbeat:
        return None

    proof = heartbeat.proof
    if proof:
        hb_proof = indexer.HbProofFields(
            hb_pk=proof.public_key,
            hb_pk1sig=proof.public_key_1_signature,
            hb_pk2=proof.public_key_2,
            hb_pk2sig=proof.public_key_2_signature,
            hb_sig=proof.signature,
        )
    else:
        hb_proof = indexer.HbProofFields()
    return indexer.TransactionHeartbeat(
        hb_proof=hb_proof,
        hb_address=heartbeat.address or ALGORAND_ZERO_ADDRESS,
        hb_key_dilution=heartbeat.key_dilution or 0,
        hb_seed=heartbeat.seed or b"",
        hb_vote_id=heartbeat.vote_id or b"",
    )


def _convert_state_proof(sp: sp_models.StateProof) -> indexer.StateProofFields:
    reveals = list[indexer.StateProofReveal]()
    if sp.reveals:
        for position, reveal in sp.reveals.items():
            reveals.append(_convert_state_proof_reveal(reveal, position))

    return indexer.StateProofFields(
        part_proofs=(_convert_merkle_array_proof(sp.part_proofs) if sp.part_proofs else None),
        sig_proofs=(_convert_merkle_array_proof(sp.sig_proofs) if sp.sig_proofs else None),
        positions_to_reveal=sp.positions_to_reveal,
        salt_version=sp.merkle_signature_salt_version or 0,
        sig_commit=sp.sig_commit,
        signed_weight=sp.signed_weight,
        reveals=reveals if reveals else None,
    )


def _convert_merkle_array_proof(
    proof: sp_models.MerkleArrayProof,
) -> indexer.MerkleArrayProof:
    return indexer.MerkleArrayProof(
        path=proof.path,
        hash_factory=(
            indexer.HashFactory(hash_type=proof.hash_factory.hash_type)
            if proof.hash_factory
            else None
        ),
        tree_depth=proof.tree_depth,
    )


def _convert_state_proof_reveal(
    reveal: sp_models.Reveal, position: int
) -> indexer.StateProofReveal:
    signature = None
    sig_slot = reveal.sigslot
    if sig_slot and sig_slot.sig:
        sig = sig_slot.sig
        signature = indexer.StateProofSignature(
            falcon_signature=sig.signature,
            merkle_array_index=sig.vector_commitment_index,
            proof=_convert_merkle_array_proof(sig.proof) if sig.proof else None,
            verifying_key=sig.verifying_key.public_key if sig.verifying_key else None,
        )
    return indexer.StateProofReveal(
        position=position,
        participant=(
            _convert_state_proof_participant(reveal.participant) if reveal.participant else None
        ),
        sig_slot=(
            indexer.StateProofSigSlot(
                lower_sig_weight=reveal.sigslot.lower_sig_weight or 0,
                signature=signature,
            )
            if reveal.sigslot
            else None
        ),
    )


def _convert_state_proof_participant(
    participant: sp_models.Participant,
) -> indexer.StateProofParticipant:
    verifier = None
    if participant.verifier:
        verifier = indexer.StateProofVerifier(
            commitment=participant.verifier.commitment,
            key_lifetime=participant.verifier.key_lifetime,
        )
    return indexer.StateProofParticipant(
        weight=participant.weight,
        verifier=verifier,
    )


def _get_synthetic_block_payout_transaction(
    block: algod.Block, intra_round_offset_iter: Iterator[int]
) -> indexer.Transaction:
    """
    Gets the synthetic transaction for the block payout as defined in the indexer

    See https://github.com/algorand/indexer/blob/084577338ad4882f5797b3e1b30b84718ad40333/idb/postgres/internal/writer/write_txn.go?plain=1#L180-L202
    """
    header = block.header

    # create an algod txn first, so then a tx_id can be derived
    algod_txn = algod.SignedTxnWithAD(
        signed_transaction=algod.SignedTransaction(
            txn=AlgodTransaction(
                transaction_type=TransactionType.Payment,
                payment=PaymentTransactionFields(
                    receiver=block.header.proposer or ALGORAND_ZERO_ADDRESS,
                    amount=block.header.proposer_payout or 0,
                ),
                sender=header.reward_state.fee_sink or ALGORAND_ZERO_ADDRESS,
                note=b"ProposerPayout for Round " + str(header.round).encode("utf-8"),
                first_valid=header.round or 0,
                last_valid=header.round or 0,
                fee=0,
                genesis_hash=header.genesis_hash,
                genesis_id=header.genesis_id,
            ),
        ),
        apply_data=None,
    )
    indexer_txn = _get_indexer_transaction_from_algod_transaction(
        block, algod_txn, intra_round_offset_iter=intra_round_offset_iter
    )
    indexer_txn.signature = indexer.TransactionSignature()
    return indexer_txn


def block_data_to_block_metadata(block_data: algod.BlockResponse) -> BlockMetadata:
    """
    Extract key metadata from a block.

    :param block_data: The raw block data
    :type block_data: algod.GetBlock
    :return: The block metadata
    :rtype: BlockMetadata
    """
    block = block_data.block
    header = block.header
    cert = block_data.cert

    # Extract block hash from certificate if available
    block_hash: str | None = None
    if cert:
        prop = cert.get("prop")
        if isinstance(prop, dict):
            dig = prop.get("dig")
            if dig is not None:
                if isinstance(dig, bytes):
                    block_hash = base64.b64encode(dig).decode("utf-8")
                elif isinstance(dig, str):
                    block_hash = dig

    reward_state = header.reward_state
    upgrade_state = header.upgrade_state
    txn_commitments = header.txn_commitments
    return BlockMetadata(
        round=header.round or 0,
        hash=block_hash,
        timestamp=header.timestamp or 0,
        genesis_id=header.genesis_id or "",
        genesis_hash=(
            base64.b64encode(header.genesis_hash).decode("utf-8") if header.genesis_hash else ""
        ),
        previous_block_hash=(
            base64.b64encode(header.previous_block_hash).decode("utf-8")
            if header.previous_block_hash
            else None
        ),
        seed=base64.b64encode(header.seed).decode("utf-8") if header.seed else "",
        parent_transaction_count=len(block.payset or []),
        full_transaction_count=count_all_transactions(
            [t.signed_transaction for t in block.payset or []]
        ),
        rewards=BlockRewards(
            fee_sink=reward_state.fee_sink or ALGORAND_ZERO_ADDRESS,
            rewards_pool=reward_state.rewards_pool or ALGORAND_ZERO_ADDRESS,
            rewards_level=reward_state.rewards_level or 0,
            rewards_residue=reward_state.rewards_residue or 0,
            rewards_rate=reward_state.rewards_rate or 0,
            rewards_calculation_round=reward_state.rewards_recalculation_round or 0,
        ),
        upgrade_state=BlockUpgradeState(
            current_protocol=upgrade_state.current_protocol or "",
            next_protocol=upgrade_state.next_protocol,
            next_protocol_approvals=upgrade_state.next_protocol_approvals,
            next_protocol_switch_on=upgrade_state.next_protocol_switch_on,
            next_protocol_vote_before=upgrade_state.next_protocol_vote_before,
        ),
        txn_counter=header.txn_counter or 0,
        transactions_root=(
            base64.b64encode(txn_commitments.native_sha512_256_commitment).decode("utf-8")
            if txn_commitments.native_sha512_256_commitment
            else ""
        ),
        transactions_root_sha256=(
            base64.b64encode(txn_commitments.sha256_commitment).decode("utf-8")
            if txn_commitments.sha256_commitment
            else ""
        ),
        proposer=header.proposer,
    )


def count_all_transactions(
    txns: Sequence[algod.SignedTxnWithAD],
) -> int:
    """Count all transactions including inner transactions recursively."""
    total = 0
    for txn in txns:
        apply_data = txn.apply_data
        if apply_data and apply_data.eval_delta and apply_data.eval_delta.inner_txns:
            total += count_all_transactions(apply_data.eval_delta.inner_txns or [])
    return total + len(txns)
