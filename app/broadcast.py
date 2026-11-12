"""
fans one encoder output stream out to any number of HTTP clients.
"""

import queue
import threading


class Client:
    """
    represents a client session tuned into the broadcast
    """

    def __init__(self, maxsize: int):
        self.q: queue.Queue[bytes | None] = queue.Queue(maxsize=maxsize)
        self.dropped = False  # set when the client is too slow to keep up


class Broadcaster:
    """
    manages clients tuned in to the stream
    """

    def __init__(self, queue_size: int = 256):
        self._queue_size = queue_size
        self._lock = threading.Lock()
        self._clients: list[Client] = []

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._clients)

    def add_client(self) -> Client:
        client = Client(self._queue_size)
        with self._lock:
            self._clients.append(client)
        return client

    def remove_client(self, client: Client) -> None:
        with self._lock:
            if client in self._clients:
                self._clients.remove(client)

    def publish(self, chunk: bytes) -> None:
        with self._lock:
            clients = list(self._clients)
        for client in clients:
            try:
                client.q.put_nowait(chunk)
            except queue.Full:
                # never let one slow client stall the others
                client.dropped = True
                self.remove_client(client)

    def close(self) -> None:
        """
        signal end-of-stream to every client.
        """
        with self._lock:
            clients = list(self._clients)
        for client in clients:
            try:
                client.q.put_nowait(None)
            except queue.Full:
                client.dropped = True
