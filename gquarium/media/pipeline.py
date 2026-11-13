"""
one run of the streaming pipeline: encoder + audio feeder + video renderer.
"""

import logging
import os
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Callable
from typing import Protocol

from gquarium.core.config import Settings
from gquarium.core.log import get_logger
from gquarium.library.models import Track
from gquarium.library.shuffle import ShuffleBag
from gquarium.media.audio import AudioFeeder
from gquarium.media.clock import Clock
from gquarium.media.encoder import build_encoder_cmd
from gquarium.media.fifo import open_writer, unblock_fifo, write_all
from gquarium.media.timeline import Timeline
from gquarium.scene.base import SceneFactory

log = get_logger(__name__)


class OutputSink(Protocol):
    """
    where the encoder's MPEG-TS bytes go (the streaming layer's Broadcaster).
    """

    def publish(self, chunk: bytes) -> None: ...

    def close(self) -> None: ...


class Pipeline:
    """
    not reusable. create a new one for each start.
    """

    def __init__(self, settings: Settings, bag: ShuffleBag, scene_factory: SceneFactory,
                 sink: OutputSink, on_exit: Callable[[], None] | None = None):
        self.settings = settings
        self._scene_factory = scene_factory
        self._sink = sink
        self.timeline = Timeline()
        self._bag = bag
        self._on_exit = on_exit
        self._stop = threading.Event()
        self._clock = Clock(settings.lead_s, self._stop)
        self._barrier = threading.Barrier(2, action=self._clock.start)
        self._dir: str | None = None
        self._fifos: list[str] = []
        self.encoder: subprocess.Popen | None = None
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._exit_notified = False
        self._stopped = False

    @property
    def temp_dir(self) -> str | None:
        return self._dir

    @property
    def running(self) -> bool:
        return self.encoder is not None and self.encoder.poll() is None and not self._stop.is_set()

    def now_playing(self) -> Track | None:
        return self.timeline.at(self._clock.now()) if self._clock.t0 is not None else None

    def start(self) -> None:
        s = self.settings
        self._dir = tempfile.mkdtemp(prefix="gq-")
        audio_fifo = os.path.join(self._dir, "audio.pcm")
        video_fifo = os.path.join(self._dir, "video.raw")
        os.mkfifo(audio_fifo)
        os.mkfifo(video_fifo)
        self._fifos = [audio_fifo, video_fifo]
        scene = self._scene_factory(self.timeline.state_at)
        feeder = AudioFeeder(s.music_dir, self._bag, self.timeline, self._clock, self._stop)
        cmd = build_encoder_cmd(s, audio_fifo, video_fifo)
        log.info("starting pipeline (%s, %dx%d@%d)", s.encoder, s.width, s.height, s.fps)
        log.debug("encoder command: %s", " ".join(cmd))
        try:
            self.encoder = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            shutil.rmtree(self._dir, ignore_errors=True)
            raise

        def audio_main() -> None:
            with open_writer(audio_fifo) as out:
                feeder.prime(out)
                self._sync()
                feeder.run(out)

        def video_main() -> None:
            with open_writer(video_fifo) as out:
                write_all(out, scene.frame(0.0))  # first frame lets ffmpeg finish probing
                self._sync()
                n = 1
                while True:
                    media_t = n / s.fps
                    data = scene.frame(media_t)
                    if not self._clock.wait_until(media_t):
                        return
                    write_all(out, data)
                    n += 1

        for name, target in (("audio", audio_main), ("video", video_main),
                             ("encoder-out", self._read_output),
                             ("encoder-err", self._read_errors)):
            thread = threading.Thread(target=self._guard(name, target), name=name, daemon=True)
            thread.start()
            self._threads.append(thread)

    def _sync(self) -> None:
        """
        wait for the other writer, then both start the shared clock together.

        ffmpeg opens and probes its inputs one after another, so each writer 
        must send a first chunk BEFORE calling this, or the two writers 
        deadlock waiting on each other.
        """
        self._barrier.wait(timeout=15)

    def _guard(self, name: str, target: Callable[[], None]) -> Callable[[], None]:
        def run() -> None:
            try:
                target()
            except (BrokenPipeError, threading.BrokenBarrierError):
                pass  # encoder died or stream is stopping
            except Exception:
                log.exception("%s thread failed", name)
            finally:
                if not self._stop.is_set():
                    log.error("%s thread ended unexpectedly", name)
                    self._notify_exit()

        return run

    def _read_output(self) -> None:
        fd = self.encoder.stdout.fileno()
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                return
            self._sink.publish(chunk)

    def _read_errors(self) -> None:
        for raw in self.encoder.stderr:
            line = raw.decode(errors="replace").rstrip()
            level = logging.DEBUG if "Guessed Channel Layout" in line else logging.WARNING
            log.log(level, "ffmpeg: %s", line)

    def _notify_exit(self) -> None:
        with self._lock:
            if self._exit_notified:
                return
            self._exit_notified = True
        self._sink.close()
        if self._on_exit:
            self._on_exit()

    def stop(self) -> None:
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
        log.info("stopping pipeline")
        self._stop.set()
        self._barrier.abort()
        if self.encoder is not None:
            self.encoder.terminate()
            try:
                self.encoder.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.encoder.kill()
                self.encoder.wait()
        for path in self._fifos:
            unblock_fifo(path)
        for thread in self._threads:
            thread.join(timeout=3)
        self._sink.close()
        if self._dir:
            shutil.rmtree(self._dir, ignore_errors=True)
