"""
composition-root tests: wiring only, no sockets, ffmpeg or sleeping.
"""

import json
from pathlib import Path

from PIL import Image

from gquarium.bootstrap import build_scene_factory, build_services
from gquarium.core.config import Settings
from gquarium.library.models import Track
from gquarium.media.timeline import Timeline
from gquarium.scene.background import load_background
from gquarium.web.controllers.health import health
from gquarium.web.request import Request
from tests.helpers import touch

W, H = 320, 180
SONG = Track(Path("a.mp3"), "Song A", "Artist A", "Album A")


def settings_for(tmp_path, **extra) -> Settings:
    return Settings.from_env({"MUSIC_DIR": str(tmp_path / "music"),
                              "ASSETS_DIR": str(tmp_path / "assets"),
                              "WIDTH": str(W), "HEIGHT": str(H), **extra})


def overlay_is_drawn(settings: Settings) -> bool:
    """
    true when a frame with a playing track differs from the bare background.
    """
    timeline = Timeline()
    timeline.add(0.0, SONG)
    scene = build_scene_factory(settings)(timeline.state_at)
    bare = load_background(settings.assets_dir, W, H).tobytes()
    return scene.frame(3.0) != bare


def test_overlay_appears_without_any_config_files(tmp_path):
    """
    validate (regression) the now-playing overlay shows on a bare install: no config, no assets
    """
    assert overlay_is_drawn(settings_for(tmp_path))


def test_overlay_appears_with_config_files_present(tmp_path):
    """
    validate (regression) config files, even unusable ones, never remove the overlay.
    sources.yml and settings.yml are not read before Phase 2, so this guards the day they are.
    """
    config = tmp_path / "config"
    config.mkdir()
    (config / "sources.yml").write_text("include: [unclosed\n  - : :")  # invalid YAML
    (config / "settings.yml").write_text("scene: static\nwidth: 99999\n")
    assert overlay_is_drawn(settings_for(tmp_path))


def test_overlay_appears_with_assets_present(tmp_path):
    """
    validate a custom background image and font folder don't remove the overlay
    """
    (tmp_path / "assets" / "backgrounds").mkdir(parents=True)
    (tmp_path / "assets" / "fonts").mkdir()
    Image.new("RGB", (400, 300), (10, 90, 120)).save(tmp_path / "assets" / "backgrounds" / "b.png")
    assert overlay_is_drawn(settings_for(tmp_path))


def test_unknown_scene_falls_back_to_static_with_a_warning(tmp_path, caplog):
    """
    validate SCENE=aquarium is accepted but warns until Phase 4 (behavior preserved)
    """
    with caplog.at_level("WARNING", logger="gquarium.bootstrap"):
        build_scene_factory(settings_for(tmp_path, SCENE="aquarium"))
    assert "not available yet" in caplog.text


def test_services_are_wired_from_settings(tmp_path):
    """
    validate build_services counts tracks, takes the short version, and stays idle
    """
    touch(tmp_path, "music", "A", "B", "one.mp3")
    touch(tmp_path, "music", "A", "B", "two.mp3")
    services = build_services(settings_for(tmp_path, APP_VERSION="deadbeefcafe", APP_NAME="gq"))
    assert services.version == "deadbeef"[:7]
    assert services.streaming.status() == {"pipeline": "idle", "tracks": 2, "clients": 0}
    body = json.loads(health(Request("GET", "/health"), services).body)
    assert body["app"] == "gq" and body["version"] == "deadbee" and body["tracks"] == 2
