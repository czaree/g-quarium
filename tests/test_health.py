import json
import threading
import urllib.error
import urllib.request

import pytest

from app.config import Settings
from app.main import create_server, get_version
from app.manager import Manager


@pytest.fixture
def base_url(tmp_path):
    # empty library; nothing is streamed
    manager = Manager(Settings(music_dir=tmp_path))
    # port 0 = pick a free port
    server = create_server(manager, "127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)

    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_health_reports_ok_and_version(base_url, monkeypatch):
    """
    validate that /health endpoint returns success and git SHA
    """
    monkeypatch.setenv("APP_VERSION", "a1b2c3d4e5f6")
    with urllib.request.urlopen(f"{base_url}/health") as resp:
            assert resp.status == 200
            data = json.load(resp)
    assert data["status"] == "ok"
    assert data["version"] == "a1b2c3d"
    assert data["pipeline"] == "idle"
    assert data["tracks"] == 0
    assert data["clients"] == 0

def test_now_playing_is_empty_when_idle(base_url):
    """
    validates /now-playing shows nothing when no clients connected
    """
    with urllib.request.urlopen(f"{base_url}/now-playing") as resp:
        assert json.load(resp) == {"playing": False}

def test_unknown_path_is_404(base_url):
    """
    validates unknown endpoint path returns 404 status
    """
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"{base_url}/invalid")
    assert exc.value.code == 404


def test_version_defaults_to_dev(monkeypatch):
    """
    validate get_version() falls back to "dev" without SHA present
    """
    monkeypatch.delenv("APP_VERSION", raising=False)
    assert get_version() == "dev"
