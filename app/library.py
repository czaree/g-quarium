"""
track discovery, tag reading (with filename fallback) and the shuffle bag.
"""

import logging
import random
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from mutagen import File as MutagenFile

log = logging.getLogger("g-quarium.library")

_TRACK_NUMBER = re.compile(r"^\s*\d{1,3}(?:\s*[-._)]\s*|\s+)")


@dataclass(frozen=True)
class Track:
    path: Path
    title: str
    artist: str = ""
    album: str = ""


def scan_tracks(root: Path, extensions: Iterable[str]) -> list[Path]:
    """
    all audio files under root (recursive), sorted. Missing root -> empty list."""
    exts = {e.lower() for e in extensions}
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts)


def _clean_title(stem: str) -> str:
    title = _TRACK_NUMBER.sub("", stem).replace("_", " ").strip()
    return title or stem.replace("_", " ").strip()


def _first(tags, key: str) -> str:
    try:
        values = tags.get(key)
    except Exception:
        return ""
    return str(values[0]).strip() if values else ""


def read_track(path: Path, root: Path) -> Track:
    """
    reads tags when present. otherwise, title from the filename and album/artist from folders.
    """
    title = artist = album = ""
    try:
        audio = MutagenFile(path, easy=True)
        if audio is not None and audio.tags:
            title = _first(audio, "title")
            artist = _first(audio, "artist")
            album = _first(audio, "album")
    except Exception as exc:  # unreadable tags must never stop playback
        log.debug("could not read tags from %s: %s", path, exc)

    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = (path.parent.name, path.name)
    if not title:
        title = _clean_title(path.stem)
    if not album and len(parts) >= 2:
        album = parts[-2]
    if not artist and len(parts) >= 3:
        artist = parts[-3]
    return Track(path=path, title=title, artist=artist, album=album)


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
