"""
audio feeder. decodes tracks to PCM and writes them, paced, into the encoder's audio pipe.
"""

import logging
import subprocess
import threading
import time

from app.config import Settings
from app.library import ShuffleBag, read_track
from app.timeline import Timeline

log = logging.getLogger("g-quarium.audio")

SAMPLE_RATE = 48000
CHANNELS = 2
BYTES_PER_FRAME = 2 * CHANNELS
BYTES_PER_SEC = SAMPLE_RATE * BYTES_PER_FRAME
CHUNK_BYTES = BYTES_PER_SEC // 10  # 100 ms


class Clock:
    """
    shared wall-clock pacing for the audio and video writers (media time starts at 0).
    """

    def __init__(self, lead_s: float, stop: threading.Event):
        self.lead = lead_s
        self.stop = stop
        self.t0: float | None = None

    def start(self) -> None:
        self.t0 = time.monotonic()

    def now(self) -> float:
        return 0.0 if self.t0 is None else time.monotonic() - self.t0

    def wait_until(self, media_t: float) -> bool:
        """
        sleep until media_t is due (minus the lead). False means the pipeline is stopping.
        """
        delay = media_t - self.lead - self.now()
        if delay > 0:
            return not self.stop.wait(delay)
        return not self.stop.is_set()


def write_all(out, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = out.write(view)
        view = view[written:]


class AudioFeeder:
    def __init__(self, settings: Settings, bag: ShuffleBag, timeline: Timeline,
                 clock: Clock, stop: threading.Event):
        self._s = settings
        self._bag = bag
        self._timeline = timeline
        self._clock = clock
        self._stop = stop
        self._sent = 0  # bytes written so far; media time = _sent / BYTES_PER_SEC

    def prime(self, out) -> None:
        """
        write 100 ms of silence immediately so ffmpeg can finish probing 
        this input and go on to open the video pipe. Counts as the first 
        100 ms of the stream.
        """
        write_all(out, bytes(CHUNK_BYTES))
        self._sent += CHUNK_BYTES

    def run(self, out) -> None:
        failures = 0
        while not self._stop.is_set():
            path = self._bag.next()
            if path is None:
                self._timeline.add(self._sent / BYTES_PER_SEC, None)
                if not self._silence(5.0, out):
                    return
                continue
            track = read_track(path, self._s.music_dir)
            played = self._play(track, out)
            if played is None:
                return  # stopping
            if played == 0:
                failures += 1
                log.warning("could not decode %s (failures in a row: %d)", path.name, failures)
                if not self._silence(min(failures, 5) * 1.0, out):
                    return
            else:
                failures = 0

    def _play(self, track, out) -> int | None:
        """
        stream one track. Returns bytes played, or None if the pipeline is stopping.
        """
        proc = subprocess.Popen(
            ["ffmpeg", "-nostdin", "-v", "error", "-i", str(track.path), "-vn",
             "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "pipe:1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        played = 0
        try:
            while True:
                chunk = proc.stdout.read(CHUNK_BYTES)
                chunk = chunk[: len(chunk) // BYTES_PER_FRAME * BYTES_PER_FRAME]
                if not chunk:
                    break
                if played == 0:
                    self._timeline.add(self._sent / BYTES_PER_SEC, track)
                    log.info("now playing: %s | %s | %s", track.title, track.artist, track.album)
                if not self._clock.wait_until(self._sent / BYTES_PER_SEC):
                    return None
                write_all(out, chunk)
                self._sent += len(chunk)
                played += len(chunk)
        finally:
            proc.kill()
            err = proc.stderr.read(2000).decode(errors="replace").strip()
            proc.wait()
            if played == 0 and err:
                log.warning("decoder said: %s", err)
        return played

    def _silence(self, seconds: float, out) -> bool:
        remaining = int(seconds * BYTES_PER_SEC) // CHUNK_BYTES * CHUNK_BYTES
        zeros = bytes(CHUNK_BYTES)
        while remaining > 0:
            if not self._clock.wait_until(self._sent / BYTES_PER_SEC):
                return False
            write_all(out, zeros)
            self._sent += CHUNK_BYTES
            remaining -= CHUNK_BYTES
        return True
