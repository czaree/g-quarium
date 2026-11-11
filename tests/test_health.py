from app.main import create_app, get_version


async def test_health_reports_ok_and_version(aiohttp_client, monkeypatch):
    """
    validate that /health endpoint returns success and git SHA
    """
    monkeypatch.setenv("APP_VERSION", "a1b2c3d4e5f6")
    client = await aiohttp_client(create_app())
    resp = await client.get("/health")
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "a1b2c3d"
    assert data["pipeline"] == "idle"


def test_version_defaults_to_dev(monkeypatch):
    """
    validate get_version() falls back to "dev" without SHA present
    """
    monkeypatch.delenv("APP_VERSION", raising=False)
    assert get_version() == "dev"
