"""
runtime settings, read from environment variables.

this module and bootstrap.py are the only places allowed to read the environment. every other
module receives the settings (or the values it needs) from its caller.
"""

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gquarium.core.version import short_version

AUDIO_EXTENSIONS = (".mp3", ".flac", ".ogg", ".m4a", ".opus", ".wav")


@dataclass(frozen=True)
class Settings:
    app_name: str = "g-quarium"
    app_version: str = "dev"  # full git SHA baked in at build time; see the version property
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
    log_level: str = "info"
    # per-module overrides, e.g. "media.pipeline=debug,web=info" (see core/log.py)
    log_levels: str = ""
    extensions: tuple[str, ...] = AUDIO_EXTENSIONS

    @property
    def version(self) -> str:
        return short_version(self.app_version)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        e = os.environ if env is None else env
        return cls(**{v.field: v.parse(e[v.name]) for v in ENV_VARS if v.name in e})


@dataclass(frozen=True)
class EnvVar:
    name: str  # environment variable
    field: str  # Settings attribute it fills
    parse: Callable[[str], Any]


# the single list of environment variables. docs/configuration.md must mention every name here
# (enforced by tests/unit/test_docs.py).
ENV_VARS: tuple[EnvVar, ...] = (
    EnvVar("APP_NAME", "app_name", str),
    EnvVar("APP_VERSION", "app_version", str),
    EnvVar("MUSIC_DIR", "music_dir", Path),
    EnvVar("ASSETS_DIR", "assets_dir", Path),
    EnvVar("ENCODER", "encoder", str.lower),
    EnvVar("VAAPI_DEVICE", "vaapi_device", str),
    EnvVar("WIDTH", "width", int),
    EnvVar("HEIGHT", "height", int),
    EnvVar("FPS", "fps", int),
    EnvVar("VIDEO_BITRATE_K", "video_bitrate_k", int),
    EnvVar("IDLE_GRACE_S", "idle_grace_s", float),
    EnvVar("NOW_PLAYING_DELAY_S", "now_playing_delay_s", float),
    EnvVar("LEAD_S", "lead_s", float),
    EnvVar("SCENE", "scene", str.lower),
    EnvVar("PORT", "port", int),
    EnvVar("LOG_LEVEL", "log_level", str),
    EnvVar("LOG_LEVELS", "log_levels", str),
)
