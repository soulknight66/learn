from __future__ import annotations

import queue
import socket
import threading
import time

from http_core import (
    CounterApp,
    HTTPParser,
    ProtocolError,
    Request,
    Response,
    ServiceConfig,
    serve_connection,
    unavailable_response,
)


ARCHITECTURE = "bounded-worker-pool"


class Server:
    def __init__(self, config: ServiceConfig | None = None, app: CounterApp | None = None) -> None:
        self.config = config or ServiceConfig()
        self.app = app or CounterApp()
        self._stopping = threading.Event()
        self._queue: queue.Queue[socket.socket | None] = queue.Queue(self.config.queue_size)
        self._listener: socket.socket | None = None
        self._acceptor: threading.Thread | None = None
        self._workers: list[threading.Thread] = []
        self._connection_lock = threading.Lock()
        self._connections: set[socket.socket] = set()
        self._address: tuple[str, int] | None = None

    @property
    def address(self) -> tuple[str, int]:
        if self._address is None:
            raise RuntimeError("server has not started")
        return self._address

    @property
    def worker_thread_count(self) -> int:
        return len(self._workers)

    def start(self) -> None:
        if self._listener is not None:
            raise RuntimeError("server already started")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.config.host, self.config.port))
        listener.listen(self.config.backlog)
        listener.settimeout(0.05)
        self._listener = listener
        host, port = listener.getsockname()[:2]
        self._address = (str(host), int(port))
        self._workers = [
            threading.Thread(target=self._worker, name=f"http-worker-{index}", daemon=True)
            for index in range(self.config.worker_count)
        ]
        for thread in self._workers:
            thread.start()
        self._acceptor = threading.Thread(
            target=self._accept, name="http-acceptor", daemon=True
        )
        self._acceptor.start()

    def _accept(self) -> None:
        assert self._listener is not None
        while not self._stopping.is_set():
            try:
                connection, _ = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                self._queue.put_nowait(connection)
            except queue.Full:
                try:
                    connection.sendall(unavailable_response())
                except OSError:
                    pass
                connection.close()

    def _worker(self) -> None:
        while True:
            connection = self._queue.get()
            try:
                if connection is None:
                    return
                with self._connection_lock:
                    self._connections.add(connection)
                try:
                    with connection:
                        serve_connection(connection, self.app, self.config, self._stopping)
                finally:
                    with self._connection_lock:
                        self._connections.discard(connection)
            finally:
                self._queue.task_done()

    def close(self) -> None:
        if self._listener is None:
            return
        deadline = time.monotonic() + self.config.shutdown_timeout
        self._stopping.set()
        self._listener.close()
        if self._acceptor is not None:
            self._acceptor.join(timeout=max(0.0, deadline - time.monotonic()))
        while True:
            try:
                pending = self._queue.get_nowait()
            except queue.Empty:
                break
            if pending is not None:
                pending.close()
            self._queue.task_done()
        with self._connection_lock:
            connections = list(self._connections)
        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        sentinels = 0
        for _ in self._workers:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                self._queue.put(None, timeout=remaining)
            except queue.Full:
                break
            sentinels += 1
        for thread in self._workers:
            thread.join(timeout=max(0.0, deadline - time.monotonic()))
        acceptor_alive = self._acceptor is not None and self._acceptor.is_alive()
        live_workers = [thread.name for thread in self._workers if thread.is_alive()]
        self._listener = None
        if acceptor_alive or live_workers or sentinels != len(self._workers):
            raise RuntimeError(
                "server did not stop within configured shutdown_timeout; "
                f"acceptor_alive={acceptor_alive} live_workers={live_workers!r}"
            )

    def __enter__(self) -> "Server":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
