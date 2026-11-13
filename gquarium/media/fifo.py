"""
named-pipe helpers. FIFOs need Linux, so only the container (and CI) runs them for real.
"""

import os

try:
    import fcntl
except ImportError:  # Windows: only the Linux container runs the pipeline
    fcntl = None

F_SETPIPE_SZ = 1031


def write_all(out, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = out.write(view)
        view = view[written:]


def unblock_fifo(path: str) -> None:
    """
    release a writer stuck in open() on a FIFO nobody is reading.
    """
    try:
        os.close(os.open(path, os.O_RDONLY | os.O_NONBLOCK))
    except OSError:
        pass


def grow_pipe(fd: int) -> None:
    if fcntl is not None:
        try:
            fcntl.fcntl(fd, F_SETPIPE_SZ, 1 << 20)
        except OSError:
            pass


def open_writer(path: str):
    """
    open a FIFO for writing (blocks until ffmpeg opens it).
    """
    fd = os.open(path, os.O_WRONLY)
    grow_pipe(fd)
    return os.fdopen(fd, "wb", buffering=0)
