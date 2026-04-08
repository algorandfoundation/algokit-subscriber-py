from algokit_algod_client import models as algod
from algokit_indexer_client import models as indexer
from algokit_transact import (
    LogicSigSignature,
    MultisigSignature,
    MultisigSubsignature,
    PaymentTransactionFields,
    Transaction,
    TransactionType,
)

from algokit_subscriber._transform import get_block_transactions

# Test data constants
GENESIS_HASH = bytes.fromhex("e062008fb39333426137530c54fb121e663ae2159155f1e73b37d555a74fef9d")

LOGIC_PROGRAM = bytes([1, 32, 1, 1, 34])
LSIG_ARGS = [bytes([1]), bytes([2, 3])]

# Multisig public keys (32 bytes each)
PUBLIC_KEY_1 = bytes.fromhex("1b7ec0b04bea61b796909796cbf407e108a705351d0bc98abeb12209a8ab8178")
PUBLIC_KEY_2 = bytes.fromhex("09633209537389f0756711773991c7d03e1b73c8c4f52bf6aff01aa25cf9c271")
PUBLIC_KEY_3 = bytes.fromhex("e7f0f84d06811df9f31c8d878b1155f4671d51a185c200908667f4495870a8a1")

# Signatures (64 bytes each)
SIGNATURE_1 = bytes.fromhex(
    "8c3365c4b1d11370f23f70d777469fe1d94779bf4d8d6481764935ef784ccc76"
    "576cc0e0efe9c146fa6076dafaceee9af31b768ebc32b4ec1a2c8c3dc06706"
)
SIGNATURE_2 = bytes.fromhex(
    "4f56d47dd9c0b16a15f58864e9e743d531091ff7af6cb281df340d153a236ea5"
    "d91773d9ff97658ef7ea63f03768cdfe28be8ac6827af371add984a738eae50d"
)


class TestPaymentLmsigLogicsig:
    """Tests for payment transaction with lmsig logicsig signature."""

    def test_correctly_handles_payment_lmsig_logicsig_signed_transaction(self) -> None:
        sender = "RWJLJCMQAFZ2ATP2INM2GZTKNL6OULCCUBO5TQPXH3V2KR4AG7U5UA5JNM"
        receiver = "PHWNJTJMA6E4RYZX4SN46QO3OYEXCB46ZIR7B7NJEN5R7PARRKZJBB4FUU"

        txn = Transaction(
            transaction_type=TransactionType.Payment,
            sender=sender,
            fee=217000,
            first_valid=9390,
            last_valid=9493,
            genesis_id="dockernet-v1",
            genesis_hash=GENESIS_HASH,
            note=bytes([180, 81, 121, 57, 252, 250, 210, 113]),
            payment=PaymentTransactionFields(
                receiver=receiver,
                amount=1000,
            ),
        )

        # Create the logic sig with multisig (lmsig)
        lsig = LogicSigSignature(
            logic=LOGIC_PROGRAM,
            args=LSIG_ARGS,
            lmsig=MultisigSignature(
                version=1,
                threshold=2,
                subsigs=[
                    MultisigSubsignature(public_key=PUBLIC_KEY_1, sig=SIGNATURE_1),
                    MultisigSubsignature(public_key=PUBLIC_KEY_2, sig=SIGNATURE_2),
                    MultisigSubsignature(public_key=PUBLIC_KEY_3, sig=None),
                ],
            ),
        )

        block = algod.BlockResponse(
            block=algod.Block(
                header=algod.BlockHeader(
                    round=9394,
                    timestamp=1758701734,
                    genesis_id="dockernet-v1",
                    genesis_hash=GENESIS_HASH,
                    previous_block_hash=bytes(32),
                    seed=bytes(32),
                    txn_commitments=algod.TxnCommitments(
                        native_sha512_256_commitment=bytes(32),
                    ),
                    reward_state=algod.RewardState(
                        fee_sink="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ",
                        rewards_pool="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ",
                        rewards_level=0,
                        rewards_rate=0,
                        rewards_residue=0,
                        rewards_recalculation_round=500000,
                    ),
                    upgrade_state=algod.UpgradeState(
                        current_protocol="https://github.com/algorandfoundation/specs/tree/953304de35264fc3ef91bcd05c123242015eeaed",
                    ),
                    participation_updates=algod.ParticipationUpdates(
                        expired_participation_accounts=(),
                        absent_participation_accounts=(),
                    ),
                    txn_counter=11271,
                ),
                payset=[
                    algod.SignedTxnInBlock(
                        signed_transaction=algod.SignedTxnWithAD(
                            signed_transaction=algod.SignedTransaction(
                                lsig=lsig,
                                txn=txn,
                            ),
                            apply_data=algod.ApplyData(),
                        ),
                        has_genesis_id=True,
                        has_genesis_hash=False,
                    )
                ],
            ),
            cert={"rnd": 9394},
        )

        transactions = get_block_transactions(block.block)

        assert len(transactions) == 1
        transaction = transactions[0]

        assert transaction.signature is not None
        assert transaction.signature.logicsig is not None

        assert transaction.signature.logicsig == indexer.TransactionSignatureLogicsig(
            logic=LOGIC_PROGRAM,
            args=LSIG_ARGS,
            signature=None,
            multisig_signature=None,
            logic_multisig_signature=indexer.TransactionSignatureMultisig(
                version=1,
                threshold=2,
                subsignature=[
                    indexer.TransactionSignatureMultisigSubsignature(
                        public_key=PUBLIC_KEY_1, signature=SIGNATURE_1
                    ),
                    indexer.TransactionSignatureMultisigSubsignature(
                        public_key=PUBLIC_KEY_2, signature=SIGNATURE_2
                    ),
                    indexer.TransactionSignatureMultisigSubsignature(
                        public_key=PUBLIC_KEY_3, signature=None
                    ),
                ],
            ),
        )
