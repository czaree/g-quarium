"""
shared fixtures: fake collaborators so controllers and the lifecycle service are tested without
ffmpeg, sockets, sleeps or Docker.
"""

from pathlib import Path

import pytest

from gquarium.core.config import Settings
from gquarium.library.models import Track
from gquarium.streaming.broadcast import Client
from gquarium.web.services import Services


class FakeStreaming:
    """
    stands in for StreamingService. records calls and never starts anything.
    """

    def __init__(self, track: Track | None = None, fail_connect: bool = False):
        self.track = track
        self.fail_connect = fail_connect
        self.clients: list[Client] = []
        self.disconnected: list[Client] = []
        self.connects = 0

    def connect(self) -> Client:
        self.connects += 1
        if self.fail_connect:
            raise RuntimeError("boom")
        client = Client(maxsize=8)
        self.clients.append(client)
        return client

    def disconnect(self, client: Client) -> None:
        self.disconnected.append(client)

    def now_playing(self) -> Track | None:
        return self.track

    def status(self) -> dict:
        return {"pipeline": "running" if self.clients else "idle", "tracks": 3,
                "clients": len(self.clients) - len(self.disconnected)}


@pytest.fixture
def song() -> Track:
    return Track(Path("a.mp3"), "Song A", "Artist A", "Album A")


@pytest.fixture
def fake_streaming() -> FakeStreaming:
    return FakeStreaming()


@pytest.fixture
def services(fake_streaming) -> Services:
    return Services(streaming=fake_streaming, settings=Settings(app_name="test-app"),
                    version="abc1234")  # type: ignore[arg-type]
