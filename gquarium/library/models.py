"""
model objects shared by the library, scene and media packages.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Track:
    path: Path
    title: str
    artist: str = ""
    album: str = ""
