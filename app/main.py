"""
g-quarium app runner. test app stub, serves /health only.
"""

import logging
import os

from aiohttp import web

log = logging.getLogger("q-quarium")


def get_version() -> str:
    """
    git SHA is stored at build time (APP_VERSION), or 'dev'.
    """
    return os.environ.get("APP_VERSION", "dev")[:7]


async def health(request: web.Request) -> web.Response:
    """
    reports the service's health. only fails if the process/HTTP server is down.

    Args:
        request (web.Request): http request made to the endpoint
    
    Returns:
        web.Response: httpresponse reporting service health
    """
    return web.json_response(
        {
            "status": "ok",
            "version": get_version(),
            "pipeline": "idle",
            "tracks": 0,
            "clients": 0,
        }
    )


def create_app() -> web.Application:
    """
    launches a new instance of the g-quarium app with /health endpoint

    Returns:
        web.Application: new g-quarium app instance
    """
    app = web.Application()
    app.router.add_get("/health", health)
    return app


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
    web.run_app(create_app(), port=int(os.environ.get("PORT", "8080")), print=None)


if __name__ == "__main__":
    main()
