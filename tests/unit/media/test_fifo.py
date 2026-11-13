from gquarium.media.fifo import write_all


class TrickleWriter:
    """
    writes at most 3 bytes per call, like a pipe under pressure.
    """

    def __init__(self):
        self.data = b""

    def write(self, view) -> int:
        part = bytes(view[:3])
        self.data += part
        return len(part)


def test_write_all_handles_partial_writes():
    """
    validate write_all keeps writing until every byte is out
    """
    out = TrickleWriter()
    write_all(out, b"0123456789")
    assert out.data == b"0123456789"
