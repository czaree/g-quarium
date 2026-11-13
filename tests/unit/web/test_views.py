from gquarium.web.views import health_view, now_playing_view


def test_now_playing_view_without_a_track():
    """
    validate silence is reported as not playing
    """
    assert now_playing_view(None) == {"playing": False}


def test_now_playing_view_with_a_track(song):
    """
    validate a track is reported with title, artist and album
    """
    assert now_playing_view(song) == {
        "playing": True, "title": "Song A", "artist": "Artist A", "album": "Album A"}


def test_health_view_includes_app_version_status_and_now_playing(song):
    """
    validate /health carries app name, version, service status and the overlay's track
    """
    body = health_view("g-quarium", "abc1234",
                       {"pipeline": "running", "tracks": 5, "clients": 1}, song)
    assert body["status"] == "ok" and body["app"] == "g-quarium" and body["version"] == "abc1234"
    assert (body["pipeline"], body["tracks"], body["clients"]) == ("running", 5, 1)
    assert body["now_playing"]["title"] == "Song A"
