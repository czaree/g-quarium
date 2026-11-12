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

from app.audio import SAMPLE_RATE, AudioFeeder, Clock, write_all
from app.broadcast import Broadcaster
from app.config import Settings
from app.library import ShuffleBag
from app.scene import Scene
from app.timeline import Timeline

log = logging.getLogger("g-quarium.pipeline")

try:
    import fcntl
except ImportError:  # Windows: only the Linux container runs the pipeline
    fcntl = None

F_SETPIPE_SZ = 1031


def build_encoder_cmd(s: Settings, audio_fifo: str, video_fifo: str) -> list[str]:
    """
    ffmpeg command: raw PCM + raw RGB frames in, MPEG-TS on stdout.

    timestamps come from sample/frame counts. Both writers are paced by one 
    Python clock, so audio and video stay aligned without ffmpeg's wall-clock
    timestamping.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning", "-nostdin",
        "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", "2",
        "-thread_queue_size", "512", "-probesize", "32", "-analyzeduration", "0",
        "-i", audio_fifo,
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-video_size", f"{s.width}x{s.height}",
        "-framerate", str(s.fps),
        "-thread_queue_size", "64", "-probesize", "32", "-analyzeduration", "0",
        "-i", video_fifo,
        "-map", "1:v", "-map", "0:a",
    ]
    bitrate = [
        "-b:v", f"{s.video_bitrate_k}k",
        "-maxrate", f"{int(s.video_bitrate_k * 1.2)}k",
        "-bufsize", f"{s.video_bitrate_k * 2}k",
        "-g", str(s.fps),  # a keyframe every second, so late joiners sync quickly
    ]
    if s.encoder == "vaapi":
        cmd += ["-vaapi_device", s.vaapi_device, "-vf", "format=nv12,hwupload",
                "-c:v", "h264_vaapi", *bitrate]
    elif s.encoder == "software":
        cmd += ["-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast",
                "-tune", "zerolatency", *bitrate]
    else:
        raise ValueError(f"unknown ENCODER {s.encoder!r} (use vaapi or software)")
    cmd += [
        "-c:a", "aac", "-b:a", "128k",
        "-f", "mpegts", "-muxdelay", "0", "-flush_packets", "1",
        "-mpegts_flags", "+resend_headers+pat_pmt_at_frames", "-pat_period", "0.5",
        "pipe:1",
    ]
    return cmd


def _unblock_fifo(path: str) -> None:
    """
    release a writer stuck in open() on a FIFO nobody is reading.
    """
    try:
        os.close(os.open(path, os.O_RDONLY | os.O_NONBLOCK))
    except OSError:
        pass


def _grow_pipe(fd: int) -> None:
    if fcntl is not None:
        try:
            fcntl.fcntl(fd, F_SETPIPE_SZ, 1 << 20)
        except OSError:
            pass


class Pipeline:
    """
    not reusable. create a new one for each start.
    """

    def __init__(self, settings: Settings, bag: ShuffleBag,
                 on_exit: Callable[[], None] | None = None):
        self.settings = settings
        self.broadcaster = Broadcaster()
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

    def now_playing(self):
        return self.timeline.at(self._clock.now()) if self._clock.t0 is not None else None

    def start(self) -> None:
        s = self.settings
        self._dir = tempfile.mkdtemp(prefix="aq-")
        audio_fifo = os.path.join(self._dir, "audio.pcm")
        video_fifo = os.path.join(self._dir, "video.raw")
        os.mkfifo(audio_fifo)
        os.mkfifo(video_fifo)
        self._fifos = [audio_fifo, video_fifo]
        scene = Scene(s, self.timeline)
        feeder = AudioFeeder(s, self._bag, self.timeline, self._clock, self._stop)
        cmd = build_encoder_cmd(s, audio_fifo, video_fifo)
        log.info("starting pipeline (%s, %dx%d@%d)", s.encoder, s.width, s.height, s.fps)
        log.debug("encoder command: %s", " ".join(cmd))
        try:
            self.encoder = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            shutil.rmtree(self._dir, ignore_errors=True)
            raise

        def audio_main() -> None:
            with self._open_writer(audio_fifo) as out:
                feeder.prime(out)
                self._sync()
                feeder.run(out)

        def video_main() -> None:
            with self._open_writer(video_fifo) as out:
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

    def _open_writer(self, path: str):
        """
        open a FIFO for writing (blocks until ffmpeg opens it).
        """
        fd = os.open(path, os.O_WRONLY)
        _grow_pipe(fd)
        return os.fdopen(fd, "wb", buffering=0)

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
            self.broadcaster.publish(chunk)

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
        self.broadcaster.close()
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
            _unblock_fifo(path)
        for thread in self._threads:
            thread.join(timeout=3)
        self.broadcaster.close()
        if self._dir:
            shutil.rmtree(self._dir, ignore_errors=True)
