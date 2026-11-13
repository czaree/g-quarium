import json

from gquarium.web.controllers.health import health
from gquarium.web.request import Request


def test_health_reports_ok_version_and_app(services):
    """
    validate /health returns 200 with status, app name and short git SHA
    """
    response = health(Request("GET", "/health"), services)
    body = json.loads(response.body)
    assert response.status == 200
    assert (body["status"], body["app"], body["version"]) == ("ok", "test-app", "abc1234")
    assert body["pipeline"] == "idle" and body["tracks"] == 3 and body["clients"] == 0


def test_health_includes_now_playing_state(services, fake_streaming, song):
    """
    validate /health shows what the overlay is showing (missing-overlay diagnostics)
    """
    fake_streaming.track = song
    body = json.loads(health(Request("GET", "/health"), services).body)
    assert body["now_playing"]["playing"] is True and body["now_playing"]["title"] == "Song A"


def test_health_never_wakes_the_pipeline(services, fake_streaming):
    """
    validate /health does not connect a client
    """
    health(Request("GET", "/health"), services)
    assert fake_streaming.connects == 0
