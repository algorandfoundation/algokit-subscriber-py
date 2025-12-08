from algokit_utils import AlgoAmount, AlgorandClient, PaymentParams


def generate_account(algorand: AlgorandClient, amount: int = int(5e6)) -> str:
    dispsener = algorand.account.localnet_dispenser().addr
    addr = algorand.account.random().addr

    algorand.send.payment(
        PaymentParams(sender=dispsener, receiver=addr, amount=AlgoAmount(micro_algo=amount))
    )

    return addr
