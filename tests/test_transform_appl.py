from algokit_algod_client import models as algod
from algokit_indexer_client import models as indexer
from algokit_transact import (
    OnApplicationComplete,
    Transaction,
    TransactionType,
)
from algokit_transact.models.app_call import (
    AppCallTransactionFields,
    BoxReference,
    HoldingReference,
    LocalsReference,
    ResourceReference,
)

from algokit_subscriber._transform import get_block_transactions

# Test data constants
GENESIS_HASH = bytes.fromhex("e062008fb39333426137530c54fb121e663ae2159155f1e73b37d555a74fef9d")
SENDER = "FDMKB5D72THLYSJEBHBDHUE7XFRDOM5IHO44SOJ7AWPD6EZMWOQ2WKN7HQ"


def _create_block_response(
    txn: Transaction,
    round_num: int = 8670,
    timestamp: int = 1758683634,
) -> algod.BlockResponse:
    return algod.BlockResponse(
        block=algod.Block(
            header=algod.BlockHeader(
                round=round_num,
                timestamp=timestamp,
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
                txn_counter=round_num + 1,
            ),
            payset=[
                algod.SignedTxnInBlock(
                    signed_transaction=algod.SignedTxnWithAD(
                        signed_transaction=algod.SignedTransaction(
                            sig=bytes(64),
                            txn=txn,
                        ),
                        apply_data=algod.ApplyData(
                            eval_delta=algod.BlockAppEvalDelta(
                                logs=[bytes.fromhex("151f7c75000b48656c6c6f2c2074657374")],
                            ),
                        ),
                    ),
                    has_genesis_id=True,
                    has_genesis_hash=False,
                )
            ],
        ),
        cert={"rnd": round_num},
    )


class TestApplicationAccessList:
    """Tests for application access list mapping."""

    def test_correctly_handles_application_access_list(self) -> None:
        txn = Transaction(
            transaction_type=TransactionType.AppCall,
            sender=SENDER,
            fee=1000,
            first_valid=8669,
            last_valid=9669,
            genesis_id="dockernet-v1",
            genesis_hash=GENESIS_HASH,
            application_call=AppCallTransactionFields(
                app_id=11270,
                on_complete=OnApplicationComplete.NoOp,
                args=[bytes.fromhex("f17e80a5"), bytes.fromhex("000474657374")],
                access_references=[
                    ResourceReference(app_id=123),
                    ResourceReference(address=SENDER),
                    ResourceReference(asset_id=54),
                    ResourceReference(holding=HoldingReference(asset_id=54, address=SENDER)),
                    ResourceReference(app_id=432),
                    ResourceReference(locals=LocalsReference(app_id=432, address=SENDER)),
                    ResourceReference(app_id=678),
                    ResourceReference(box=BoxReference(app_id=678, name=bytes([1, 2, 3]))),
                ],
            ),
        )

        block_response = _create_block_response(txn)
        transactions = get_block_transactions(block_response.block)

        assert len(transactions) == 1
        access = transactions[0].application_transaction.access  # type: ignore[union-attr]
        assert access == [
            indexer.ResourceRef(application_id=123),
            indexer.ResourceRef(address=SENDER),
            indexer.ResourceRef(asset_id=54),
            indexer.ResourceRef(holding=indexer.HoldingRef(address=SENDER, asset=54)),
            indexer.ResourceRef(application_id=432),
            indexer.ResourceRef(local=indexer.LocalsRef(address=SENDER, app=432)),
            indexer.ResourceRef(application_id=678),
            indexer.ResourceRef(box=indexer.BoxReference(app=678, name=bytes([1, 2, 3]))),
        ]


class TestApplicationRejectVersion:
    """Tests for application reject version mapping."""

    def test_correctly_handles_application_reject_version(self) -> None:
        sender = "B65C7U64OR6JBRROKUV4OEXZXDSLFZCRAI4QXWARW3GCF7TBMT5BSCOLGE"

        txn = Transaction(
            transaction_type=TransactionType.AppCall,
            sender=sender,
            fee=0,
            first_valid=23055,
            last_valid=24055,
            genesis_id="dockernet-v1",
            genesis_hash=GENESIS_HASH,
            application_call=AppCallTransactionFields(
                app_id=28639,
                on_complete=OnApplicationComplete.NoOp,
                args=[bytes.fromhex("f17e80a5"), bytes.fromhex("000568656c6c6f")],
                reject_version=3,
            ),
        )

        block_response = _create_block_response(txn, round_num=23056, timestamp=1758786416)
        transactions = get_block_transactions(block_response.block)

        assert len(transactions) == 1
        assert transactions[0].application_transaction is not None
        assert transactions[0].application_transaction.reject_version == 3

    def test_reject_version_is_none_when_not_set(self) -> None:
        sender = "B65C7U64OR6JBRROKUV4OEXZXDSLFZCRAI4QXWARW3GCF7TBMT5BSCOLGE"

        txn = Transaction(
            transaction_type=TransactionType.AppCall,
            sender=sender,
            fee=0,
            first_valid=23055,
            last_valid=24055,
            genesis_id="dockernet-v1",
            genesis_hash=GENESIS_HASH,
            application_call=AppCallTransactionFields(
                app_id=28639,
                on_complete=OnApplicationComplete.NoOp,
            ),
        )

        block_response = _create_block_response(txn, round_num=23056, timestamp=1758786416)
        transactions = get_block_transactions(block_response.block)

        assert len(transactions) == 1
        assert transactions[0].application_transaction is not None
        assert transactions[0].application_transaction.reject_version is None
