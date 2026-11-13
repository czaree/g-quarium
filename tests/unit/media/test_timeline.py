from pathlib import Path

from gquarium.library.models import Track
from gquarium.media.timeline import Timeline


def test_returns_the_track_playing_at_a_given_time():
    """
    validate timeline correctly tracks what song should be playing
    at any given timestamp
    """
    a, b = Track(Path("a"), "A"), Track(Path("b"), "B")
    t = Timeline()
    assert t.at(1.0) is None
    t.add(0.0, a)
    t.add(10.0, b)
    assert t.at(5.0) == a
    assert t.at(10.0) == b
    assert t.at(99.0) == b


def test_none_marks_silence():
    """
    validate no track playing returns no audio track object
    """
    t = Timeline()
    t.add(0.0, Track(Path("a"), "A"))
    t.add(4.0, None)
    assert t.at(5.0) is None
