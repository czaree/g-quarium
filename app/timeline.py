"""
maps media time (seconds since the stream started) to the current track 
playing then.
"""

import threading

from app.library import Track


class Timeline:
    def __init__(self, keep: int = 16):
        self._lock = threading.Lock()
        self._events: list[tuple[float, Track | None]] = []
        self._keep = keep

    def add(self, media_t: float, track: Track | None) -> None:
        with self._lock:
            self._events.append((media_t, track))
            del self._events[: -self._keep]

    def state_at(self, media_t: float) -> tuple[float, Track | None]:
        """
        (media time the current entry began, track) at media_t. (0.0, None) if nothing yet.
        """
        with self._lock:
            result: tuple[float, Track | None] = (0.0, None)
            for start, track in self._events:
                if start <= media_t:
                    result = (start, track)
                else:
                    break
            return result

    def at(self, media_t: float) -> Track | None:
        return self.state_at(media_t)[1]
