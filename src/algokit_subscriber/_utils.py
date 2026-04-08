from algokit_common import sha512_256


def method_selector_bytes(method_signature: str) -> bytes:
    return sha512_256(method_signature.encode("utf-8"))[:4]
