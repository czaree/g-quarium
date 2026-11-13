"""
HTTP transport only. parses the socket request into a Request, asks the router for a controller,
and writes the Response. it knows no endpoints.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gquarium.core.log import get_logger
from gquarium.web.request import Request
from gquarium.web.responses import Response, StreamResponse
from gquarium.web.router import Router
from gquarium.web.services import Services

log = get_logger(__name__)


class Handler(BaseHTTPRequestHandler):
    server_version = "Gquarium"

    def _handle(self) -> None:
        path, _, query = self.path.partition("?")
        request = Request(self.command, path, query, self.address_string())
        controller = self.server.router.resolve(request.method, request.path)
        try:
            response = controller(request, self.server.services)
        except Exception:
            log.exception("controller failed for %s %s", request.method, request.path)
            self.send_error(500)
            return
        if isinstance(response, StreamResponse):
            self._write_stream(response)
        else:
            self._write(response)

    # every method goes to the router, which answers 405 for the ones a path doesn't support
    do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _handle

    def _send_head(self, response: Response, length: int | None) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        if length is not None:
            self.send_header("Content-Length", str(length))
        for name, value in response.headers.items():
            self.send_header(name, value)
        self.end_headers()

    def _write(self, response: Response) -> None:
        body = response.body
        self._send_head(response, len(body))
        if self.command != "HEAD":
            self.wfile.write(body)

    def _write_stream(self, response: StreamResponse) -> None:
        try:
            self._send_head(response, None)
            for chunk in response.chunks:
                self.wfile.write(chunk)
        except OSError:
            pass  # the viewer went away
        finally:
            close = getattr(response.chunks, "close", None)
            if close:
                close()
            response.on_close()

    def log_message(self, fmt: str, *args) -> None:
        log.debug("%s - %s", self.address_string(), fmt % args)


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], router: Router, services: Services):
        super().__init__(address, Handler)
        self.router = router
        self.services = services


def create_server(router: Router, services: Services, host: str = "0.0.0.0",
                  port: int = 8080) -> Server:
    return Server((host, port), router, services)
