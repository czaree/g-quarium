"""
fonts and text fitting.
"""

from collections.abc import Sequence
from pathlib import Path

from PIL import ImageFont

from gquarium.core.log import get_logger

log = get_logger(__name__)

FONT_EXTS = {".ttf", ".otf", ".ttc"}
# System fonts tried after your own assets/fonts: DejaVu (Latin, Greek,
# Cyrillic, installed in the Docker image) and Noto CJK (Chinese/Japanese/Korean).
SYSTEM_FONTS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)


def has_glyph(font, char: str) -> bool:
    """
    true if the font really draws this character (not its 'missing glyph'
    box).
    """
    return bytes(font.getmask(char)) != bytes(font.getmask("\uffff"))


def fit_text(text: str, font, max_width: float) -> str:
    """
    shorten text with an ellipsis so it fits max_width pixels.
    """
    if font.getlength(text) <= max_width:
        return text
    while text and font.getlength(text + "…") > max_width:
        text = text[:-1]
    return text.rstrip() + "…"


class FontSet:
    def __init__(self, assets_dir: Path, system_fonts: Sequence[str] = SYSTEM_FONTS):
        self._assets = assets_dir
        self._system_fonts = system_fonts
        self._fonts: dict[int, list] = {}

    def candidates(self, size: int) -> list:
        """
        fonts in priority order: local assets/fonts, system fonts,
        Pillow's built-in.
        """
        if size not in self._fonts:
            paths: list[str] = []
            folder = self._assets / "fonts"
            if folder.is_dir():
                paths += [str(p) for p in sorted(folder.iterdir()) if p.suffix.lower() in FONT_EXTS]
            paths += [p for p in self._system_fonts if Path(p).is_file()]
            fonts = []
            for path in paths:
                try:
                    fonts.append(ImageFont.truetype(path, size))
                except Exception as exc:
                    log.warning("skipping unreadable font %s: %s", path, exc)
            fonts.append(ImageFont.load_default(size=size))
            self._fonts[size] = fonts
        return self._fonts[size]

    def font_for(self, text: str, size: int):
        """
        first font that has every character in the text (else the first font).
        """
        fonts = self.candidates(size)
        chars = {c for c in text if not c.isspace()}
        for font in fonts:
            if all(has_glyph(font, c) for c in chars):
                return font
        return fonts[0]
