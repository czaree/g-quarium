"""
g-quarium app runner. test app stub, serves /health only.
"""

import logging
import os
import json
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("q-quarium")


def get_version() -> str:
    """
    git SHA is stored at build time (APP_VERSION), or 'dev'.
    """
    return os.environ.get("APP_VERSION", "dev")[:7]


def health_payload() -> dict:
    """
    reports the service's health. only fails if the process/HTTP server is down.

    Returns:
        dict: response body reporting service health
    """
    return {
        "status": "ok",
        "version": get_version(),
        "pipeline": "idle",
        "tracks": 0,
        "clients": 0,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "AquariumRadio"

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send_json(200, health_payload())
        else:
            self._send_json(404, {"error": "not found"})

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        log.debug("%s - %s", self.address_string(), fmt % args)


def create_server(host: str = "0.0.0.0", port: int = 8080) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server

def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "info").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info(
        "g-quarium starting version=%s encoder=%s tracks=%d",
        get_version(),
        os.environ.get("ENCODER", "vaapi"),
        0,
    )
    server = create_server(port=int(os.environ.get("PORT", "8080")))

    # as PID 1 in a container, Python ignores SIGTERM unless a handler is installed.
    # without this, `docker stop` waits 10s and then SIGKILLs.
    def stop(signum, frame):
        log.info("shutting down")
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    server.serve_forever()
    server.server_close()


if __name__ == "__main__":
    main()
