import queue
from collections.abc import Iterator

from gquarium.core.log import get_logger
from gquarium.streaming.broadcast import Client
from gquarium.web.request import Request
from gquarium.web.responses import JsonResponse, Response, StreamResponse
from gquarium.web.services import Services

log = get_logger(__name__)


def _chunks(client: Client) -> Iterator[bytes]:
    while not client.dropped:
        try:
            chunk = client.q.get(timeout=1.0)
        except queue.Empty:
            continue
        if chunk is None:  # pipeline ended
            return
        yield chunk


def stream(request: Request, services: Services) -> Response:
    try:
        client = services.streaming.connect()
    except Exception:
        log.exception("could not start the pipeline")
        return JsonResponse({"error": "pipeline failed to start"}, status=503)
    log.info("viewer connected: %s", request.client)

    def on_close() -> None:
        if client.dropped:
            log.warning("viewer %s was too slow and was dropped", request.client)
        services.streaming.disconnect(client)
        log.info("viewer disconnected: %s", request.client)

    return StreamResponse(_chunks(client), on_close, content_type="video/mp2t",
                          headers={"Cache-Control": "no-store"})
