"""
composition root: builds settings, logging, services and the server, and runs them.

this and core/config.py are the only modules that read the environment, and this is the only
one that decides which concrete classes get built.
"""

import signal
import threading
from dataclasses import dataclass

from gquarium.core.config import Settings
from gquarium.core.log import configure_logging, get_logger
from gquarium.library.shuffle import ShuffleBag
from gquarium.library.sources import DirectorySource
from gquarium.media.pipeline import Pipeline
from gquarium.scene.base import NowPlaying, SceneFactory, SceneRenderer
from gquarium.scene.static import StaticScene
from gquarium.streaming.broadcast import Broadcaster
from gquarium.streaming.service import PipelineHandle, StreamingService
from gquarium.web.router import Router
from gquarium.web.server import Server, create_server
from gquarium.web.services import Services

log = get_logger(__name__)


def build_scene_factory(settings: Settings) -> SceneFactory:
    if settings.scene != "static":
        log.warning("SCENE=%s is not available yet; using the static scene", settings.scene)

    def factory(now_playing: NowPlaying) -> SceneRenderer:
        return StaticScene(settings, now_playing)

    return factory


def build_services(settings: Settings) -> Services:
    source = DirectorySource(settings.music_dir, settings.extensions)
    bag = ShuffleBag(source.scan)
    scene_factory = build_scene_factory(settings)

    def pipeline_factory(sink: Broadcaster, on_exit) -> PipelineHandle:
        return Pipeline(settings, bag, scene_factory, sink, on_exit)

    streaming = StreamingService(bag, pipeline_factory, settings.idle_grace_s)
    return Services(streaming=streaming, settings=settings, version=settings.version)


@dataclass(frozen=True)
class App:
    services: Services
    server: Server

    def shutdown(self) -> None:
        self.services.streaming.shutdown()
        self.server.server_close()


def build_app(settings: Settings, host: str = "0.0.0.0", port: int | None = None) -> App:
    services = build_services(settings)
    server = create_server(Router(), services, host, settings.port if port is None else port)
    return App(services, server)


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.app_name, settings.log_level, settings.log_levels)
    app = build_app(settings)
    log.info("%s starting version=%s encoder=%s tracks=%d", settings.app_name, settings.version,
             settings.encoder, app.services.streaming.track_count)

    # as PID 1 in a container, Python ignores SIGTERM unless a handler is installed.
    # without this, `docker stop` waits 10s and then SIGKILLs.
    def stop(signum, frame):
        log.info("shutting down")
        threading.Thread(target=app.server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        app.server.serve_forever()
    finally:
        app.shutdown()
