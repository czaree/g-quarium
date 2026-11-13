"""
end-to-end check with real ffmpeg. Skipped where FIFOs or ffmpeg aren't available
(for example native Windows). it runs in CI and inside the Linux container.
"""

import os
import queue
import time

import pytest

from gquarium.bootstrap import build_services
from gquarium.core.config import Settings
from tests.integration.conftest import SAMPLES, requires_linux_and_ffmpeg

pytestmark = [pytest.mark.integration, requires_linux_and_ffmpeg]


def test_pipeline_streams_mpegts_and_cleans_up(tmp_path):
    settings = Settings(music_dir=SAMPLES, assets_dir=tmp_path, encoder="software",
                        width=320, height=180, fps=10, lead_s=0.3, idle_grace_s=0.2)
    streaming = build_services(settings).streaming
    client = streaming.connect()
    pipeline = streaming._pipeline
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
        assert streaming.status()["pipeline"] == "running"
        assert streaming.now_playing() is not None
    finally:
        streaming.disconnect(client)
        streaming.shutdown()
    assert pipeline.encoder.poll() is not None, "encoder still running after shutdown"
    assert not os.path.exists(pipeline.temp_dir), "temp FIFO folder not removed"
