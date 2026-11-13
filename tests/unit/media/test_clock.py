import threading

from gquarium.media.clock import Clock


class FakeTime:
    def __init__(self):
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_media_time_follows_the_injected_time_source():
    """
    validate media time starts at 0 and advances with the injected clock (no sleeping)
    """
    t = FakeTime()
    clock = Clock(0.5, threading.Event(), t)
    assert clock.now() == 0.0  # not started
    clock.start()
    t.now += 3.25
    assert clock.now() == 3.25


def test_wait_until_returns_immediately_when_due():
    """
    validate chunks already due (within the lead) are released without waiting
    """
    t = FakeTime()
    clock = Clock(0.5, threading.Event(), t)
    clock.start()
    t.now += 10
    assert clock.wait_until(5.0) is True
    assert clock.wait_until(10.4) is True  # due: 10.4 - lead 0.5 < now 10


def test_wait_until_reports_stop():
    """
    validate a stopping pipeline makes wait_until return False (also when it would have waited)
    """
    stop = threading.Event()
    clock = Clock(0.0, stop, FakeTime())
    clock.start()
    stop.set()
    assert clock.wait_until(0.0) is False
    assert clock.wait_until(1000.0) is False  # Event.wait returns at once when already set
