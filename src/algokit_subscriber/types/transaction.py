from enum import Enum, IntEnum

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

AnyTransaction = (
    Transaction
    | AssetConfigTxn
    | ApplicationCallTxn
    | AssetFreezeTxn
    | AssetTransferTxn
    | PaymentTxn
    | KeyregTxn
    | StateProofTxn
)


class TransactionType(Enum):
    """
    Enum representing different transaction types.
    """

    # Payment transaction
    pay = "pay"

    # Key registration transaction
    keyreg = "keyreg"

    # Asset configuration transaction
    acfg = "acfg"

    # Asset transfer transaction
    axfer = "axfer"

    # Asset freeze transaction
    afrz = "afrz"

    # Application transaction
    appl = "appl"

    # State proof transaction
    stpf = "stpf"


class AlgodOnComplete(IntEnum):
    """
    Enum representing the different types of application completion.
    """

    NoOpOC = 0
    """
    NoOpOC indicates that an application transaction will simply call its
    ApprovalProgram
    """

    OptInOC = 1
    """
    OptInOC indicates that an application transaction will allocate some
    LocalState for the application in the sender's account
    """

    CloseOutOC = 2
    """
    CloseOutOC indicates that an application transaction will deallocate
    some LocalState for the application from the user's account
    """

    ClearStateOC = 3
    """
    ClearStateOC is similar to CloseOutOC, but may never fail. This
    allows users to reclaim their minimum balance from an application
    they no longer wish to opt in to.
    """

    UpdateApplicationOC = 4
    """
    UpdateApplicationOC indicates that an application transaction will
    update the ApprovalProgram and ClearStateProgram for the application
    """

    DeleteApplicationOC = 5
    """
    DeleteApplicationOC indicates that an application transaction will
    delete the AppParams for the application from the creator's balance
    record
    """


class IndexerOnComplete(Enum):
    """
    Enum representing the different types of application completion.
    """

    noop = "noop"
    optin = "optin"
    closeout = "closeout"
    clear = "clear"
    update = "update"
    delete = "delete"
