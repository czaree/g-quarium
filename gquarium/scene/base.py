"""
the scene extension point. a scene turns media time into a raw RGB frame.

scene never imports media: the overlay is handed a now-playing callable and bootstrap wires the
pipeline's timeline into it.
"""

from collections.abc import Callable
from typing import Protocol

from gquarium.library.models import Track

# media_t -> (media time the current entry began, track or None for silence)
NowPlaying = Callable[[float], tuple[float, Track | None]]


class SceneRenderer(Protocol):
    def frame(self, media_t: float) -> bytes:
        """
        raw RGB bytes (width x height x 3) for the given media time.
        """
        ...


# builds a fresh renderer for each pipeline run, given that run's now-playing source
SceneFactory = Callable[[NowPlaying], SceneRenderer]
