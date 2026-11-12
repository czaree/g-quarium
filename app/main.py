"""
g-quarium app runner. http server running stream pipeline
"""

import json
import logging
import os
import queue
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.config import Settings
from app.manager import Manager

log = logging.getLogger("q-quarium")


def get_version() -> str:
    """
    git SHA is stored at build time (APP_VERSION), or 'dev'.
    """
    return os.environ.get("APP_VERSION", "dev")[:7]


def health_payload(manager: Manager) -> dict:
    """
    reports the service's health. only fails if the process/HTTP server is down.

    Returns:
        dict: response body reporting service health
    """
    return {
        "status": "ok",
        "version": get_version(),
        "pipeline": "idle",
        **manager.status()
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "Gquarium"

    @property
    def manager(self) -> Manager:
        return self.server.manager

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send_json(200, health_payload(self.manager))
        elif path == "/now-playing":
            track = self.manager.now_playing()
            body = {"playing": track is not None}
            if track:
                body.update(title=track.title, artist=track.artist, album=track.album)
            self._send_json(200, body)
        elif path == "/stream.ts":
            self._stream()
        else:
            self._send_json(404, {"error": "not found"})

    def _stream(self) -> None:
            try:
                client = self.manager.connect()
            except Exception:
                log.exception("could not start the pipeline")
                self._send_json(503, {"error": "pipeline failed to start"})
                return
            log.info("viewer connected: %s", self.address_string())
            try:
                self.send_response(200)
                self.send_header("Content-Type", "video/mp2t")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                while not client.dropped:
                    try:
                        chunk = client.q.get(timeout=1.0)
                    except queue.Empty:
                        continue
                    if chunk is None:  # pipeline ended
                        break
                    self.wfile.write(chunk)
            except OSError:
                pass
            finally:
                if client.dropped:
                    log.warning("viewer %s was too slow and was dropped", self.address_string())
                self.manager.disconnect(client)
                log.info("viewer disconnected: %s", self.address_string())

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        log.debug("%s - %s", self.address_string(), fmt % args)


def create_server(manager: Manager, host: str = "0.0.0.0", port: int = 8080) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.manager = manager
    return server

def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "info").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings.from_env()
    manager = Manager(settings)
    
    log.info(
        "g-quarium starting version=%s encoder=%s tracks=%d",
        get_version(), 
        settings.encoder, 
        manager.track_count
    )

    if settings.scene != "static":
            log.warning("SCENE=%s is not available yet; using the static scene", settings.scene)
    server = create_server(manager, port=settings.port)

    # as PID 1 in a container, Python ignores SIGTERM unless a handler is installed.
    # without this, `docker stop` waits 10s and then SIGKILLs.
    def stop(signum, frame):
        log.info("shutting down")
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    
    try:
        server.serve_forever()
    finally:
        manager.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
