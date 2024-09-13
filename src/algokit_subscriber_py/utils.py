import logging
from collections.abc import Callable
from typing import TypeVar

from algosdk.encoding import encode_address as sdk_encode_address

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def range_inclusive(start: int, end: int) -> list[int]:
    return list(range(start, end + 1))


T = TypeVar("T")


def chunk_array(arr: list[T], size: int) -> list[list[T]]:
    return [arr[i : i + size] for i in range(0, len(arr), size)]


def reduce(array: list[T], callback: Callable[[T, T], T]) -> T:
    iterator = iter(array)
    accumulator: T = next(iterator)

    for item in iterator:
        accumulator = callback(accumulator, item)

    return accumulator


def encode_address(b: bytes) -> str:
    return sdk_encode_address(b)  # type: ignore[no-untyped-call,no-any-return]
