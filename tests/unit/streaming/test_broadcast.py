from gquarium.streaming.broadcast import Broadcaster


def test_every_client_gets_every_chunk():
    """
    validate multiple clients each receive all stream chunks
    """
    b = Broadcaster()
    c1, c2 = b.add_client(), b.add_client()
    b.publish(b"x")
    b.publish(b"y")
    assert [c1.q.get_nowait(), c1.q.get_nowait()] == [b"x", b"y"]
    assert [c2.q.get_nowait(), c2.q.get_nowait()] == [b"x", b"y"]


def test_slow_client_is_dropped_without_blocking_others():
    """
    validate broadcaster drops slow client without impacting service to others
    """
    b = Broadcaster(queue_size=2)
    slow, fast = b.add_client(), b.add_client()
    for i in range(4):
        b.publish(bytes([i]))
        fast.q.get_nowait()  # the fast client keeps up
    assert slow.dropped and not fast.dropped
    assert b.count == 1


def test_close_signals_end_of_stream():
    """
    validate client signals close when stream ends
    """
    b = Broadcaster()
    c = b.add_client()
    b.close()
    assert c.q.get_nowait() is None


def test_remove_client():
    """
    validate remove_client() correctly removes a client
    """
    b = Broadcaster()
    c = b.add_client()
    b.remove_client(c)
    assert b.count == 0
