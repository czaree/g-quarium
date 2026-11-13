"""
pure functions that turn model objects into JSON-ready data (and, later, M3U / XMLTV text).
formatting lives here and nowhere else.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gquarium.library.models import Track


def now_playing_view(track: Track | None) -> dict:
    body: dict = {"playing": track is not None}
    if track:
        body.update(title=track.title, artist=track.artist, album=track.album)
    return body


def health_view(app_name: str, version: str, status: Mapping, track: Track | None) -> dict:
    """
    the service's health. 'ok' only means the process and HTTP server are up; an idle pipeline
    is a normal state.
    """
    return {
        "status": "ok",
        "app": app_name,
        "version": version,
        **status,
        "now_playing": now_playing_view(track),
    }
