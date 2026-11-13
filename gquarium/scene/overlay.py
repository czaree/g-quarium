"""
the now-playing card: drawn once per track change, composited onto every frame.
"""

from PIL import Image, ImageDraw

from gquarium.library.models import Track
from gquarium.scene.text import FontSet, fit_text

FADE_S = 1.0


class Overlay:
    def __init__(self, width: int, height: int, fonts: FontSet, app_name: str):
        self._w, self._h = width, height
        self._fonts = fonts
        self._app_name = app_name
        self._card: Image.Image | None = None
        self._card_xy = (0, 0)

    def render(self, track: Track | None) -> None:
        h, w = self._h, self._w
        pad, margin = int(h * 0.03), int(h * 0.05)
        label_size = max(10, int(h * 0.03))
        title_size = max(14, int(h * 0.055))
        sub_size = max(11, int(h * 0.038))
        max_text_w = int(w * 0.6) - 2 * pad

        if track is None:
            label, title = self._app_name.upper(), "No music found"
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
                font = self._fonts.font_for(text, size)
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

    def composite(self, background: Image.Image, fade: float) -> Image.Image:
        """
        a copy of background with the card drawn on it at the given opacity (0 to 1).
        """
        frame = background.copy()
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
