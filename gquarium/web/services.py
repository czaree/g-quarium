"""
the small container of collaborators handed to every controller (there are no globals).
bootstrap.py builds it once.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gquarium.core.config import Settings
    from gquarium.streaming.service import StreamingService


@dataclass(frozen=True)
class Services:
    streaming: StreamingService
    settings: Settings
    version: str
