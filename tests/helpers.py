"""
small shared test helpers.
"""

from pathlib import Path


def touch(root: Path, *parts: str) -> Path:
    """
    create a placeholder audio file (not real audio) under root and return its path.
    """
    path = root.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not really audio")
    return path
