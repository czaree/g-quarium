from gquarium.web.request import Request
from gquarium.web.responses import JsonResponse, Response
from gquarium.web.services import Services
from gquarium.web.views import now_playing_view


def now_playing(request: Request, services: Services) -> Response:
    return JsonResponse(now_playing_view(services.streaming.now_playing()))
