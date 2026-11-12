"""
on-demand lifecycle. start the pipeline for the first viewer, stop after 
all clients disconnect.
"""

import logging
import threading
from collections.abc import Callable

from app.broadcast import Client
from app.config import Settings
from app.library import ShuffleBag, Track, scan_tracks
from app.pipeline import Pipeline

log = logging.getLogger("g-quarium.manager")


class Manager:
    def __init__(self, settings: Settings,
                 pipeline_factory: Callable[..., Pipeline] = Pipeline):
        self.settings = settings
        self._factory = pipeline_factory
        self._bag = ShuffleBag(lambda: scan_tracks(settings.music_dir, settings.extensions))
        self._lock = threading.Lock()
        self._pipeline: Pipeline | None = None
        self._timer: threading.Timer | None = None
        self._bag.prime()

    @property
    def track_count(self) -> int:
        return self._bag.size

    def connect(self) -> Client:
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            if self._pipeline is None:
                pipeline = self._factory(self.settings, self._bag, on_exit=self._pipeline_died)
                pipeline.start()
                self._pipeline = pipeline
            return self._pipeline.broadcaster.add_client()

    def disconnect(self, client: Client) -> None:
        with self._lock:
            pipeline = self._pipeline
            if pipeline is None:
                return
            pipeline.broadcaster.remove_client(client)
            if pipeline.broadcaster.count == 0 and self._timer is None:
                log.info("last viewer left; stopping in %.0fs", self.settings.idle_grace_s)
                self._timer = threading.Timer(self.settings.idle_grace_s, self._idle_stop)
                self._timer.daemon = True
                self._timer.start()

    def _idle_stop(self) -> None:
        with self._lock:
            self._timer = None
            pipeline = self._pipeline
            if pipeline is None or pipeline.broadcaster.count > 0:
                return
            self._pipeline = None
        pipeline.stop()

    def _pipeline_died(self) -> None:
        """
        called from a pipeline thread when the encoder or a feeder ends unexpectedly.
        """
        def cleanup() -> None:
            with self._lock:
                pipeline, self._pipeline = self._pipeline, None
            if pipeline is not None:
                pipeline.stop()

        threading.Thread(target=cleanup, daemon=True).start()

    def now_playing(self) -> Track | None:
        pipeline = self._pipeline
        return pipeline.now_playing() if pipeline else None

    def status(self) -> dict:
        pipeline = self._pipeline
        return {
            "pipeline": "running" if pipeline and pipeline.running else "idle",
            "tracks": self.track_count,
            "clients": pipeline.broadcaster.count if pipeline else 0,
        }

    def shutdown(self) -> None:
        with self._lock:
            if self._timer:
                self._timer.cancel()
            pipeline, self._pipeline = self._pipeline, None
        if pipeline is not None:
            pipeline.stop()


