"""
the parsed HTTP request that controllers receive
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: str = ""
    client: str = ""  # the caller's address, for logs
