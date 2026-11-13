"""
the shuffle bag: every track once per cycle, in random order.
"""

import random
from collections.abc import Callable
from pathlib import Path


class ShuffleBag:
    """
    plays every track once per cycle in random order, then rescans and reshuffles.
    """

    def __init__(self, scan: Callable[[], list[Path]], rng: random.Random | None = None):
        self._scan = scan
        self._rng = rng or random.Random()
        self._queue: list[Path] = []
        self._last: Path | None = None
        self.size = 0

    def prime(self) -> int:
        self.size = len(self._scan())
        return self.size

    def next(self) -> Path | None:
        if not self._queue:
            self._refill()
        if not self._queue:
            return None
        self._last = self._queue.pop()
        return self._last

    def _refill(self) -> None:
        items = list(self._scan())
        self.size = len(items)
        self._rng.shuffle(items)
        # never repeat the track that just played
        if len(items) > 1 and items[-1] == self._last:
            items[0], items[-1] = items[-1], items[0]
        self._queue = items
