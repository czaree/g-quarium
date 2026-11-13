"""
shared pacing for the audio and video writers (media time starts at 0).
"""

import threading
import time
from collections.abc import Callable


class Clock:
    """
    the time source is injectable so tests can drive time without sleeping.
    """

    def __init__(self, lead_s: float, stop: threading.Event,
                 time_source: Callable[[], float] = time.monotonic):
        self.lead = lead_s
        self.stop = stop
        self._time = time_source
        self.t0: float | None = None

    def start(self) -> None:
        self.t0 = self._time()

    def now(self) -> float:
        return 0.0 if self.t0 is None else self._time() - self.t0

    def wait_until(self, media_t: float) -> bool:
        """
        sleep until media_t is due (minus the lead). False means the pipeline is stopping.
        """
        delay = media_t - self.lead - self.now()
        if delay > 0:
            return not self.stop.wait(delay)
        return not self.stop.is_set()
