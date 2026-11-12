"""
runtime settings, read from environment variables.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

AUDIO_EXTENSIONS = (".mp3", ".flac", ".ogg", ".m4a", ".opus", ".wav")


@dataclass(frozen=True)
class Settings:
    music_dir: Path = Path("/music")
    assets_dir: Path = Path("/assets")
    encoder: str = "vaapi"  # vaapi | software
    vaapi_device: str = "/dev/dri/renderD128"
    width: int = 854
    height: int = 480
    fps: int = 15
    video_bitrate_k: int = 1500
    idle_grace_s: float = 30.0
    # now_playing_delay_s shifts which track the overlay shows relative 
    # to the audio. The overlay is burned into the same stream as the
    # audio, so 0 is already in sync.
    now_playing_delay_s: float = 0.0
    # How far ahead of the wall clock audio/video are fed to the encoder.
    lead_s: float = 0.5
    scene: str = "static"
    port: int = 8080
    extensions: tuple[str, ...] = AUDIO_EXTENSIONS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        e = os.environ if env is None else env
        d = cls()
        return cls(
            music_dir=Path(e.get("MUSIC_DIR", str(d.music_dir))),
            assets_dir=Path(e.get("ASSETS_DIR", str(d.assets_dir))),
            encoder=e.get("ENCODER", d.encoder).lower(),
            vaapi_device=e.get("VAAPI_DEVICE", d.vaapi_device),
            width=int(e.get("WIDTH", d.width)),
            height=int(e.get("HEIGHT", d.height)),
            fps=int(e.get("FPS", d.fps)),
            video_bitrate_k=int(e.get("VIDEO_BITRATE_K", d.video_bitrate_k)),
            idle_grace_s=float(e.get("IDLE_GRACE_S", d.idle_grace_s)),
            now_playing_delay_s=float(e.get("NOW_PLAYING_DELAY_S", d.now_playing_delay_s)),
            lead_s=float(e.get("LEAD_S", d.lead_s)),
            scene=e.get("SCENE", d.scene).lower(),
            port=int(e.get("PORT", d.port)),
        )
