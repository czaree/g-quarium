"""
the HTTP layer over a real socket: the only place sockets are used. the full app is wired by
bootstrap; the stream test also needs real ffmpeg.
"""

import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from gquarium.bootstrap import build_app
from gquarium.core.config import Settings
from tests.integration.conftest import SAMPLES, requires_linux_and_ffmpeg

pytestmark = pytest.mark.integration


@pytest.fixture
def make_app(tmp_path):
    apps = []

    def make(**overrides):
        settings = Settings(music_dir=overrides.pop("music_dir", tmp_path / "empty"),
                            assets_dir=tmp_path, encoder="software", **overrides)
        app = build_app(settings, "127.0.0.1", 0)  # port 0 = pick a free port
        threading.Thread(target=app.server.serve_forever, daemon=True).start()
        apps.append(app)
        return app, f"http://127.0.0.1:{app.server.server_address[1]}"

    yield make
    for app in apps:
        app.server.shutdown()
        app.shutdown()


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=5) as resp:
        return resp.status, json.load(resp)


def test_health_reports_ok_version_and_app(make_app):
    """
    validate /health returns success, the short git SHA, the app name and an idle pipeline
    """
    _, base = make_app(app_version="a1b2c3d4e5f6", app_name="gq")
    status, data = get_json(f"{base}/health")
    assert status == 200
    assert (data["status"], data["app"], data["version"]) == ("ok", "gq", "a1b2c3d")
    assert (data["pipeline"], data["tracks"], data["clients"]) == ("idle", 0, 0)
    assert data["now_playing"] == {"playing": False}


def test_health_defaults_to_dev_version(make_app):
    """
    validate a build without a git SHA reports 'dev'
    """
    _, base = make_app()
    assert get_json(f"{base}/health")[1]["version"] == "dev"


def test_now_playing_is_empty_when_idle(make_app):
    """
    validate /now-playing shows nothing when no clients are connected
    """
    _, base = make_app()
    assert get_json(f"{base}/now-playing")[1] == {"playing": False}


def test_unknown_path_is_404(make_app):
    """
    validate an unknown endpoint returns 404
    """
    _, base = make_app()
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base}/invalid", timeout=5)
    assert exc.value.code == 404


def test_wrong_method_is_405(make_app):
    """
    validate a known endpoint with the wrong method returns 405 and an Allow header
    """
    _, base = make_app()
    req = urllib.request.Request(f"{base}/health", data=b"x", method="POST")
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req, timeout=5)
    assert exc.value.code == 405 and exc.value.headers["Allow"] == "GET"


@requires_linux_and_ffmpeg
def test_end_to_end_health_now_playing_and_stream(make_app):
    """
    validate over a real socket: stream MPEG-TS, see the client and track on /health and
    /now-playing, then return to idle after the grace period
    """
    _, base = make_app(music_dir=SAMPLES, width=320, height=180, fps=10, lead_s=0.3,
                       idle_grace_s=0.5)
    with urllib.request.urlopen(f"{base}/stream.ts", timeout=20) as stream:
        assert stream.status == 200 and stream.headers["Content-Type"] == "video/mp2t"
        data = b""
        deadline = time.monotonic() + 20
        while len(data) < 188 * 100 and time.monotonic() < deadline:
            data += stream.read(188 * 100 - len(data))
        assert len(data) >= 188 * 100, "no stream data within 20s"
        assert all(data[i] == 0x47 for i in range(0, 188 * 100, 188))
        health = get_json(f"{base}/health")[1]
        assert health["pipeline"] == "running" and health["clients"] == 1
        assert health["now_playing"]["playing"] is True
        assert get_json(f"{base}/now-playing")[1]["playing"] is True
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if get_json(f"{base}/health")[1]["pipeline"] == "idle":
            break
        time.sleep(0.2)
    else:
        pytest.fail("pipeline did not go idle after the last viewer left")
