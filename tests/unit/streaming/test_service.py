import random
import threading
from pathlib import Path

from gquarium.library.shuffle import ShuffleBag
from gquarium.streaming.service import StreamingService


class FakePipeline:
    def __init__(self, sink, on_exit):
        self.sink, self.on_exit = sink, on_exit
        self.started = self.stopped = False
        self.stopped_event = threading.Event()

    @property
    def running(self) -> bool:
        return self.started and not self.stopped

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True
        self.sink.close()
        self.stopped_event.set()

    def now_playing(self):
        return None


class FakeTimer:
    def __init__(self, interval, fn):
        self.interval, self.fn = interval, fn
        self.started = self.cancelled = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        if self.started and not self.cancelled:
            self.fn()


class Harness:
    def __init__(self, tracks=3, grace=30.0):
        self.pipelines: list[FakePipeline] = []
        self.timers: list[FakeTimer] = []
        bag = ShuffleBag(lambda: [Path(f"{i}.mp3") for i in range(tracks)], random.Random(1))
        self.service = StreamingService(bag, self._pipeline, grace, self._timer)

    def _pipeline(self, sink, on_exit):
        self.pipelines.append(FakePipeline(sink, on_exit))
        return self.pipelines[-1]

    def _timer(self, interval, fn):
        self.timers.append(FakeTimer(interval, fn))
        return self.timers[-1]


def test_idle_until_the_first_client_connects():
    """
    validate nothing starts at boot and the track count is known up front
    """
    h = Harness(tracks=3)
    assert h.pipelines == []
    assert h.service.status() == {"pipeline": "idle", "tracks": 3, "clients": 0}


def test_first_client_starts_the_pipeline_and_later_ones_share_it():
    """
    validate one pipeline serves several clients
    """
    h = Harness()
    h.service.connect()
    h.service.connect()
    assert len(h.pipelines) == 1 and h.pipelines[0].started
    assert h.service.status()["clients"] == 2
    assert h.service.status()["pipeline"] == "running"


def test_last_client_leaving_starts_the_grace_timer():
    """
    validate the idle timer uses the configured grace and only starts when nobody is left
    """
    h = Harness(grace=12.0)
    a, b = h.service.connect(), h.service.connect()
    h.service.disconnect(a)
    assert h.timers == []
    h.service.disconnect(b)
    assert len(h.timers) == 1 and h.timers[0].interval == 12.0 and h.timers[0].started


def test_grace_timer_firing_stops_the_pipeline():
    """
    validate nobody reconnecting within the grace period stops the pipeline and ends clients
    """
    h = Harness()
    c = h.service.connect()
    h.service.disconnect(c)
    h.timers[0].fire()
    assert h.pipelines[0].stopped
    assert h.service.status()["pipeline"] == "idle"


def test_reconnecting_during_grace_cancels_the_timer():
    """
    validate a new client during the grace period keeps the same pipeline running
    """
    h = Harness()
    c = h.service.connect()
    h.service.disconnect(c)
    h.service.connect()
    assert h.timers[0].cancelled
    h.timers[0].fire()  # a cancelled timer must not stop anything
    assert not h.pipelines[0].stopped and len(h.pipelines) == 1


def test_timer_firing_with_a_client_present_does_not_stop():
    """
    validate the stop callback re-checks the client count (race with a late connect)
    """
    h = Harness()
    c = h.service.connect()
    h.service.disconnect(c)
    h.service.connect()
    h.timers[0].fn()  # fire even though it was cancelled, as a real race could
    assert not h.pipelines[0].stopped


def test_new_pipeline_after_a_stop():
    """
    validate a fresh pipeline (and broadcaster) is built after an idle stop
    """
    h = Harness()
    c = h.service.connect()
    h.service.disconnect(c)
    h.timers[0].fire()
    h.service.connect()
    assert len(h.pipelines) == 2 and h.pipelines[1].started


def test_unexpected_pipeline_exit_is_cleaned_up():
    """
    validate a dead encoder stops the pipeline and the next client gets a new one
    """
    h = Harness()
    h.service.connect()
    h.pipelines[0].on_exit()
    assert h.pipelines[0].stopped_event.wait(timeout=5)  # returns as soon as the cleanup ran
    h.service.connect()
    assert len(h.pipelines) == 2


def test_shutdown_stops_everything():
    """
    validate shutdown cancels the timer and stops the pipeline
    """
    h = Harness()
    c = h.service.connect()
    h.service.disconnect(c)
    h.service.shutdown()
    assert h.timers[0].cancelled and h.pipelines[0].stopped
    h.service.shutdown()  # safe to repeat
