from dataclasses import dataclass

import algokit_subscriber.types.subscription as sub


def in_memory_watermark(initial_watermark: int = 0) -> sub.WatermarkPersistence:
    """A simple in memory watermark persistence"""

    @dataclass
    class _Watermark:
        value: int

        def get(self) -> int:
            return self.value

        def set(self, value: int) -> None:
            self.value = value

    watermark = _Watermark(initial_watermark)
    return sub.WatermarkPersistence(
        get=watermark.get,
        set=watermark.set,
    )
