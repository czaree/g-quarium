"""
tag reading, with filename and folder-name fallback.
"""

import re
from pathlib import Path

from mutagen import File as MutagenFile

from gquarium.core.log import get_logger
from gquarium.library.models import Track

log = get_logger(__name__)

_TRACK_NUMBER = re.compile(r"^\s*\d{1,3}(?:\s*[-._)]\s*|\s+)")


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
