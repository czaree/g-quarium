import json

from gquarium.web.controllers.now_playing import now_playing
from gquarium.web.request import Request


def test_empty_when_idle(services):
    """
    validate nothing is playing when no pipeline runs
    """
    assert json.loads(now_playing(Request("GET", "/now-playing"), services).body) == {
        "playing": False}


def test_reports_the_current_track(services, fake_streaming, song):
    """
    validate the current track is returned
    """
    fake_streaming.track = song
    body = json.loads(now_playing(Request("GET", "/now-playing"), services).body)
    assert body["playing"] is True and body["artist"] == "Artist A"
