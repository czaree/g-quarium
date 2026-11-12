"""
scene renderer. background plus now-playing overlay, as raw RGB frames.
"""

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.config import Settings
from app.library import Track
from app.timeline import Timeline

log = logging.getLogger("aquarium-radio.scene")

FADE_S = 1.0
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
FONT_EXTS = {".ttf", ".otf", ".ttc"}
# System fonts tried after your own assets/fonts: DejaVu (Latin, Greek, 
# Cyrillic, installed in the Docker image) and Noto CJK (Chinese/Japanese/Korean).
SYSTEM_FONTS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)


def load_background(assets_dir: Path, width: int, height: int) -> Image.Image:
    folder = assets_dir / "backgrounds"
    candidates = (
        sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if folder.is_dir()
        else []
    )
    for path in candidates:
        try:
            img = Image.open(path).convert("RGB")
            return ImageOps.fit(img, (width, height), Image.Resampling.LANCZOS)
        except Exception as exc:
            log.warning("skipping unreadable background %s: %s", path.name, exc)
    # no usable image: a simple deep-water gradient (lighter at the top).
    gradient = Image.linear_gradient("L").resize((width, height))
    return ImageOps.colorize(gradient, black="#1f7a99", white="#071c33").convert("RGB")


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


class Scene:
    def __init__(self, settings: Settings, timeline: Timeline):
        self._w, self._h = settings.width, settings.height
        self._delay = settings.now_playing_delay_s
        self._timeline = timeline
        self._assets = settings.assets_dir
        self._bg = load_background(settings.assets_dir, self._w, self._h)
        self._fonts: dict[int, list] = {}
        self._track: Track | None = None
        self._started = False
        self._change_t = 0.0
        self._card: Image.Image | None = None
        self._card_xy = (0, 0)
        self._cached: bytes | None = None

    def _candidates(self, size: int) -> list:
        """
        fonts in priority order: local assets/fonts, system fonts, 
        Pillow's built-in.
        """
        if size not in self._fonts:
            paths: list[str] = []
            folder = self._assets / "fonts"
            if folder.is_dir():
                paths += [str(p) for p in sorted(folder.iterdir()) if p.suffix.lower() in FONT_EXTS]
            paths += [p for p in SYSTEM_FONTS if Path(p).is_file()]
            fonts = []
            for path in paths:
                try:
                    fonts.append(ImageFont.truetype(path, size))
                except Exception as exc:
                    log.warning("skipping unreadable font %s: %s", path, exc)
            fonts.append(ImageFont.load_default(size=size))
            self._fonts[size] = fonts
        return self._fonts[size]

    def _font_for(self, text: str, size: int):
        """
        first font that has every character in the text (else the first font).
        """
        fonts = self._candidates(size)
        chars = {c for c in text if not c.isspace()}
        for font in fonts:
            if all(has_glyph(font, c) for c in chars):
                return font
        return fonts[0]

    def _make_card(self, track: Track | None) -> None:
        h, w = self._h, self._w
        pad, margin = int(h * 0.03), int(h * 0.05)
        label_size = max(10, int(h * 0.03))
        title_size = max(14, int(h * 0.055))
        sub_size = max(11, int(h * 0.038))
        max_text_w = int(w * 0.6) - 2 * pad

        if track is None:
            label, title = "G_QUARIUM", "No music found"
            sub = "Add audio files to the music folder"
        else:
            label, title = "NOW PLAYING", track.title
            sub = " · ".join(part for part in (track.artist, track.album) if part)
        lines = []
        for text, size, color in (
            (label, label_size, (170, 215, 235, 255)),
            (title, title_size, (255, 255, 255, 255)),
            (sub, sub_size, (215, 230, 240, 255)),
        ):
            if text:
                font = self._font_for(text, size)
                lines.append((fit_text(text, font, max_text_w), font, color))

        gap = int(h * 0.01)
        heights = [font.getbbox("Ag")[3] for _, font, _ in lines]
        text_w = max(int(font.getlength(text)) for text, font, _ in lines)
        card_w = text_w + 2 * pad
        card_h = sum(heights) + gap * (len(lines) - 1) + 2 * pad

        card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)
        draw.rounded_rectangle((0, 0, card_w - 1, card_h - 1), radius=pad, fill=(0, 0, 0, 150))
        y = pad
        for (text, font, color), height in zip(lines, heights, strict=True):
            draw.text((pad, y), text, font=font, fill=color)
            y += height + gap
        self._card = card
        self._card_xy = (margin, h - margin - card_h)

    def _compose(self, fade: float) -> Image.Image:
        frame = self._bg.copy()
        card = self._card
        if card is None or fade <= 0:
            return frame
        if fade < 1.0:
            card = card.copy()
            card.putalpha(card.getchannel("A").point(lambda a: int(a * fade)))
        x, y = self._card_xy
        region = frame.crop((x, y, x + card.width, y + card.height)).convert("RGBA")
        frame.paste(Image.alpha_composite(region, card).convert("RGB"), (x, y))
        return frame

    def frame(self, media_t: float) -> bytes:
        """
        raw RGB bytes (width x height x 3) for the given media time.
        """
        shifted = media_t - self._delay
        start, track = self._timeline.state_at(shifted)
        if not self._started or track != self._track or start != self._change_t:
            self._started = True
            self._track = track
            self._change_t = start
            self._make_card(track)
            self._cached = None
        fade = min(1.0, max(0.0, (shifted - start) / FADE_S))
        if fade >= 1.0 and self._cached is not None:
            return self._cached  # static scene: no re-render between track changes
        data = self._compose(fade).tobytes()
        self._cached = data if fade >= 1.0 else None
        return data
