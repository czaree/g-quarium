from gquarium.web.request import Request
from gquarium.web.responses import JsonResponse, Response
from gquarium.web.services import Services
from gquarium.web.views import health_view


def health(request: Request, services: Services) -> Response:
    """
    never touches the encoder, so it never wakes the pipeline.
    """
    streaming = services.streaming
    return JsonResponse(health_view(services.settings.app_name, services.version,
                                    streaming.status(), streaming.now_playing()))
