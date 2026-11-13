"""
what controllers return. the server turns these into bytes on the socket.
"""

import json
from collections.abc import Callable, Iterator, Mapping


class Response:
    def __init__(self, status: int = 200, content_type: str = "text/plain; charset=utf-8",
                 headers: Mapping[str, str] | None = None):
        self.status = status
        self.content_type = content_type
        self.headers = dict(headers or {})

    @property
    def body(self) -> bytes:
        return b""


class TextResponse(Response):
    def __init__(self, text: str, status: int = 200,
                 content_type: str = "text/plain; charset=utf-8",
                 headers: Mapping[str, str] | None = None):
        super().__init__(status, content_type, headers)
        self.text = text

    @property
    def body(self) -> bytes:
        return self.text.encode()


class JsonResponse(Response):
    def __init__(self, payload: Mapping, status: int = 200,
                 headers: Mapping[str, str] | None = None):
        super().__init__(status, "application/json", headers)
        self.payload = payload

    @property
    def body(self) -> bytes:
        return json.dumps(self.payload).encode()


class StreamResponse(Response):
    """
    an endless body. the server pumps `chunks` to the socket and ALWAYS calls `on_close`,
    which is how the streaming service learns a viewer left.
    """

    def __init__(self, chunks: Iterator[bytes], on_close: Callable[[], None],
                 content_type: str = "video/mp2t", status: int = 200,
                 headers: Mapping[str, str] | None = None):
        super().__init__(status, content_type, headers)
        self.chunks = chunks
        self.on_close = on_close
