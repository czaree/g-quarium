"""
background image loading.
"""

from pathlib import Path

from PIL import Image, ImageOps

from gquarium.core.log import get_logger

log = get_logger(__name__)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


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
    # no usable image, fall back to a simple water-like gradient
    gradient = Image.linear_gradient("L").resize((width, height))
    return ImageOps.colorize(gradient, black="#1f7a99", white="#071c33").convert("RGB")
