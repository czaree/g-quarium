import json

from gquarium.web.responses import JsonResponse, StreamResponse, TextResponse


def test_json_response_body():
    """
    validate JSON bodies, status and content type
    """
    r = JsonResponse({"a": 1}, status=201)
    assert json.loads(r.body) == {"a": 1} and r.status == 201
    assert r.content_type == "application/json"


def test_text_response_body():
    """
    validate text bodies are UTF-8 encoded
    """
    assert TextResponse("héllo").body == "héllo".encode()


def test_stream_response_carries_chunks_and_close_callback():
    """
    validate a stream response holds its iterator and on_close hook
    """
    closed = []
    r = StreamResponse(iter([b"a", b"b"]), lambda: closed.append(1))
    assert list(r.chunks) == [b"a", b"b"] and r.content_type == "video/mp2t"
    r.on_close()
    assert closed == [1]
