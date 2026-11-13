import os
import shutil
from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parents[2] / "samples" / "music"

requires_linux_and_ffmpeg = pytest.mark.skipif(
    not hasattr(os, "mkfifo") or shutil.which("ffmpeg") is None,
    reason="needs os.mkfifo and ffmpeg",
)
