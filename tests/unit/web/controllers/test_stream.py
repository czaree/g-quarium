from gquarium.web.controllers.stream import stream
from gquarium.web.request import Request
from gquarium.web.responses import StreamResponse

REQUEST = Request("GET", "/stream.ts", client="1.2.3.4")


def test_stream_is_mpegts_and_not_cached(services):
    """
    validate stream responses are video/mp2t with no-store caching
    """
    response = stream(REQUEST, services)
    assert isinstance(response, StreamResponse)
    assert response.status == 200 and response.content_type == "video/mp2t"
    assert response.headers["Cache-Control"] == "no-store"


def test_chunks_flow_until_the_pipeline_ends(services, fake_streaming):
    """
    validate chunks are yielded in order and a None marker ends the stream
    """
    response = stream(REQUEST, services)
    q = fake_streaming.clients[0].q
    q.put(b"a")
    q.put(b"b")
    q.put(None)
    assert list(response.chunks) == [b"a", b"b"]


def test_dropped_client_ends_the_stream(services, fake_streaming):
    """
    validate a client dropped by the broadcaster stops being served
    """
    response = stream(REQUEST, services)
    fake_streaming.clients[0].dropped = True
    assert list(response.chunks) == []


def test_closing_disconnects_the_client(services, fake_streaming):
    """
    validate on_close tells the streaming service a viewer left
    """
    response = stream(REQUEST, services)
    response.on_close()
    assert fake_streaming.disconnected == fake_streaming.clients


def test_pipeline_failure_is_a_503(services, fake_streaming):
    """
    validate a pipeline that cannot start gives 503 instead of crashing the server
    """
    fake_streaming.fail_connect = True
    response = stream(REQUEST, services)
    assert response.status == 503 and b"pipeline failed to start" in response.body
