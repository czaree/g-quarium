"""
on-demand lifecycle. start the pipeline for the first viewer, stop after
all clients disconnect.

the pipeline factory and the timer factory are injected, so lifecycle tests never start ffmpeg
or sleep.
"""

import threading
from collections.abc import Callable
from typing import Protocol

from gquarium.core.log import get_logger
from gquarium.library.models import Track
from gquarium.library.shuffle import ShuffleBag
from gquarium.streaming.broadcast import Broadcaster, Client

log = get_logger(__name__)


class PipelineHandle(Protocol):
    """
    what the service needs from a pipeline (media.pipeline.Pipeline satisfies it).
    """

    @property
    def running(self) -> bool: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def now_playing(self) -> Track | None: ...


class TimerHandle(Protocol):
    def start(self) -> None: ...

    def cancel(self) -> None: ...


# (broadcaster the pipeline publishes into, callback for an unexpected exit) -> a new pipeline
PipelineFactory = Callable[[Broadcaster, Callable[[], None]], PipelineHandle]
TimerFactory = Callable[[float, Callable[[], None]], TimerHandle]


def threading_timer(interval: float, fn: Callable[[], None]) -> TimerHandle:
    timer = threading.Timer(interval, fn)
    timer.daemon = True
    return timer


class StreamingService:
    """
    stream backend. coordinates the audio and media stream being played and serving
    content to connected clients
    """
    def __init__(self, bag: ShuffleBag, pipeline_factory: PipelineFactory, idle_grace_s: float,
                 timer_factory: TimerFactory = threading_timer):
        self._bag = bag
        self._factory = pipeline_factory
        self._grace = idle_grace_s
        self._timer_factory = timer_factory
        self._lock = threading.Lock()
        self._pipeline: PipelineHandle | None = None
        self._broadcaster: Broadcaster | None = None
        self._timer: TimerHandle | None = None
        self._bag.prime()

    @property
    def track_count(self) -> int:
        return self._bag.size

    def connect(self) -> Client:
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            if self._pipeline is None or self._broadcaster is None:
                broadcaster = Broadcaster()
                pipeline = self._factory(broadcaster, self._pipeline_died)
                pipeline.start()
                self._pipeline, self._broadcaster = pipeline, broadcaster
            return self._broadcaster.add_client()

    def disconnect(self, client: Client) -> None:
        with self._lock:
            broadcaster = self._broadcaster
            if self._pipeline is None or broadcaster is None:
                return
            broadcaster.remove_client(client)
            if broadcaster.count == 0 and self._timer is None:
                log.info("last viewer left; stopping in %.0fs", self._grace)
                self._timer = self._timer_factory(self._grace, self._idle_stop)
                self._timer.start()

    def _idle_stop(self) -> None:
        with self._lock:
            self._timer = None
            pipeline, broadcaster = self._pipeline, self._broadcaster
            if pipeline is None or (broadcaster is not None and broadcaster.count > 0):
                return
            self._pipeline = self._broadcaster = None
        pipeline.stop()

    def _pipeline_died(self) -> None:
        """
        called from a pipeline thread when the encoder or a feeder ends unexpectedly.
        stopping joins the pipeline's threads, so it must happen on a different thread.
        """
        def cleanup() -> None:
            with self._lock:
                pipeline, self._pipeline, self._broadcaster = self._pipeline, None, None
            if pipeline is not None:
                pipeline.stop()

        threading.Thread(target=cleanup, daemon=True).start()

    def now_playing(self) -> Track | None:
        pipeline = self._pipeline
        return pipeline.now_playing() if pipeline else None

    def status(self) -> dict:
        pipeline, broadcaster = self._pipeline, self._broadcaster
        return {
            "pipeline": "running" if pipeline and pipeline.running else "idle",
            "tracks": self.track_count,
            "clients": broadcaster.count if pipeline and broadcaster else 0,
        }

    def shutdown(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
            pipeline, self._pipeline, self._broadcaster = self._pipeline, None, None
        if pipeline is not None:
            pipeline.stop()
