"""
end-to-end check with real ffmpeg. Skipped where FIFOs or ffmpeg aren't available
(for example native Windows). it runs in CI and inside the Linux container.
"""

import os
import queue
import shutil
import time
from pathlib import Path

import pytest

from app.config import Settings
from app.manager import Manager

pytestmark = pytest.mark.skipif(
    not hasattr(os, "mkfifo") or shutil.which("ffmpeg") is None,
    reason="needs os.mkfifo and ffmpeg",
)

SAMPLES = Path(__file__).parent.parent / "samples" / "music"


def test_pipeline_streams_mpegts_and_cleans_up():
    settings = Settings(music_dir=SAMPLES, assets_dir=SAMPLES, encoder="software",
                        width=320, height=180, fps=10, lead_s=0.3, idle_grace_s=0.2)
    manager = Manager(settings)
    client = manager.connect()
    pipeline = manager._pipeline
    data = b""
    deadline = time.monotonic() + 20
    try:
        while len(data) < 188 * 200 and time.monotonic() < deadline:
            try:
                chunk = client.q.get(timeout=1)
            except queue.Empty:
                continue
            assert chunk is not None, "stream ended early"
            data += chunk
        assert len(data) >= 188 * 200, "no stream data within 20s"
        # MPEG-TS packets are 188 bytes and each starts with sync byte 0x47
        assert all(data[i] == 0x47 for i in range(0, 188 * 200, 188))
        assert manager.status()["pipeline"] == "running"
        assert manager.now_playing() is not None
    finally:
        manager.disconnect(client)
        manager.shutdown()
    assert pipeline.encoder.poll() is not None, "encoder still running after shutdown"
    assert not os.path.exists(pipeline.temp_dir), "temp FIFO folder not removed"
