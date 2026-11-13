"""
build identification. the git SHA is baked into the image at build time (see the Dockerfile).
"""

DEFAULT_VERSION = "dev"
SHORT_LENGTH = 7


def short_version(raw: str) -> str:
    """
    first 7 characters of the build's git SHA, or 'dev' when built without one.
    """
    return (raw or DEFAULT_VERSION)[:SHORT_LENGTH]
