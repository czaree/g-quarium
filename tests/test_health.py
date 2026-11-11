import json
import threading
import urllib.error
import urllib.request

import pytest

from app.main import create_server, get_version

@pytest.fixture
def base_url():
    server = create_server("127.0.0.1", 0)  # port 0 = pick a free port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


async def test_health_reports_ok_and_version(base_url, monkeypatch):
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
