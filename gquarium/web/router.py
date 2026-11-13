"""
the route table. maps (method, path) to a controller. the server knows no endpoints.
"""

from collections.abc import Callable, Mapping

from gquarium.web.controllers.health import health
from gquarium.web.controllers.now_playing import now_playing
from gquarium.web.controllers.stream import stream
from gquarium.web.request import Request
from gquarium.web.responses import JsonResponse, Response
from gquarium.web.services import Services

Controller = Callable[[Request, Services], Response]

ROUTES: dict[tuple[str, str], Controller] = {
    ("GET", "/health"): health,
    ("GET", "/now-playing"): now_playing,
    ("GET", "/stream.ts"): stream,
}


def not_found(request: Request, services: Services) -> Response:
    return JsonResponse({"error": "not found"}, status=404)


def method_not_allowed(allowed: list[str]) -> Controller:
    def controller(request: Request, services: Services) -> Response:
        return JsonResponse({"error": "method not allowed"}, status=405,
                            headers={"Allow": ", ".join(allowed)})

    return controller


class Router:
    def __init__(self, routes: Mapping[tuple[str, str], Controller] = ROUTES):
        self._routes = dict(routes)

    def resolve(self, method: str, path: str) -> Controller:
        """
        the controller for this request. unknown paths give 404, known paths with the wrong
        method 405.
        """
        controller = self._routes.get((method, path))
        if controller is not None:
            return controller
        allowed = sorted(m for m, p in self._routes if p == path)
        return method_not_allowed(allowed) if allowed else not_found
