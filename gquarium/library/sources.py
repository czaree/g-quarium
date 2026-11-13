"""
where the shuffle bag's tracks come from.

TrackSource is the extension point
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class TrackSource(Protocol):
    def scan(self) -> list[Path]:
        """
        the audio files currently eligible to play.
        """
        ... # TODO: make the thing


def scan_tracks(root: Path, extensions: Iterable[str]) -> list[Path]:
    """
    all audio files under root (recursive), sorted. Missing root -> empty list.
    """
    exts = {e.lower() for e in extensions}
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts)


@dataclass(frozen=True)
class DirectorySource:
    """
    read in everything under one folder (today's behavior).
    """

    root: Path
    extensions: tuple[str, ...]

    def scan(self) -> list[Path]:
        return scan_tracks(self.root, self.extensions)
