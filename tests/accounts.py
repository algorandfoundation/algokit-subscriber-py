from algokit_utils.beta.algorand_client import AlgorandClient
from algokit_utils.beta.composer import PayParams


def generate_account(algorand: AlgorandClient, amount: int = int(5e6)) -> str:
    dispsener = algorand.account.dispenser().address
    addr = algorand.account.random().address

    algorand.send.payment(PayParams(sender=dispsener, receiver=addr, amount=amount))

    return addr
