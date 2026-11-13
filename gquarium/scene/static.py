"""
the static scene: one background plus the now-playing overlay.
"""

from gquarium.core.config import Settings
from gquarium.core.log import get_logger
from gquarium.library.models import Track
from gquarium.scene.background import load_background
from gquarium.scene.base import NowPlaying
from gquarium.scene.overlay import FADE_S, Overlay
from gquarium.scene.text import FontSet

log = get_logger(__name__)


class StaticScene:
    def __init__(self, settings: Settings, now_playing: NowPlaying):
        self._delay = settings.now_playing_delay_s
        self._now_playing = now_playing
        self._bg = load_background(settings.assets_dir, settings.width, settings.height)
        self._overlay = Overlay(settings.width, settings.height, FontSet(settings.assets_dir),
                                settings.app_name)
        self._track: Track | None = None
        self._started = False
        self._change_t = 0.0
        self._cached: bytes | None = None

    def frame(self, media_t: float) -> bytes:
        """
        raw RGB bytes (width x height x 3) for the given media time.
        """
        shifted = media_t - self._delay
        start, track = self._now_playing(shifted)
        if not self._started or track != self._track or start != self._change_t:
            self._started = True
            self._track = track
            self._change_t = start
            self._overlay.render(track)
            self._cached = None
            log.debug("overlay switched to %s (media_t=%.2fs, entry began at %.2fs, delay=%.1fs)",
                      f"{track.title!r}" if track else "no track", media_t, start, self._delay)
        fade = min(1.0, max(0.0, (shifted - start) / FADE_S))
        if fade >= 1.0 and self._cached is not None:
            return self._cached  # static scene: no re-render between track changes
        data = self._overlay.composite(self._bg, fade).tobytes()
        self._cached = data if fade >= 1.0 else None
        return data
