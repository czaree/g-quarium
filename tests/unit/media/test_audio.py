import io
import threading
from pathlib import Path

from gquarium.media.audio import BYTES_PER_SEC, CHUNK_BYTES, AudioFeeder
from gquarium.media.timeline import Timeline


class FakeBag:
    def __init__(self, paths):
        self._paths = list(paths)

    def next(self):
        return self._paths.pop(0) if self._paths else None


class StopAfter:
    """
    a Clock stand-in that is always due and stops the feeder after n writes.
    """

    def __init__(self, stop: threading.Event, n: int):
        self.stop, self.left = stop, n

    def wait_until(self, media_t: float) -> bool:
        self.left -= 1
        if self.left < 0:
            self.stop.set()
        return not self.stop.is_set()


def make_feeder(bag, n):
    stop = threading.Event()
    timeline = Timeline()
    feeder = AudioFeeder(Path("/music"), bag, timeline, StopAfter(stop, n), stop)
    return feeder, timeline


def test_prime_writes_100ms_of_silence():
    """
    validate the priming chunk is 100 ms of silence
    """
    feeder, _ = make_feeder(FakeBag([]), 0)
    out = io.BytesIO()
    feeder.prime(out)
    assert out.getvalue() == bytes(CHUNK_BYTES) and CHUNK_BYTES == BYTES_PER_SEC // 10


def test_empty_library_writes_silence_and_marks_the_timeline():
    """
    validate with no track the audio stream stays continuous and the timeline records silence
    """
    feeder, timeline = make_feeder(FakeBag([]), 7)
    out = io.BytesIO()
    feeder.prime(out)
    feeder.run(out)
    assert len(out.getvalue()) > CHUNK_BYTES
    assert set(out.getvalue()) == {0}
    assert timeline.state_at(0.1) == (0.1, None)
