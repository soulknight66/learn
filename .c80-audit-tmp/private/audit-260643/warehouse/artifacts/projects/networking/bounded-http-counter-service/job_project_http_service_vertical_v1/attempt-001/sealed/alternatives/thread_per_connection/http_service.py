from __future__ import annotations

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


ARCHITECTURE = "bounded-thread-per-connection"


class Server:
    def __init__(self, config: ServiceConfig | None = None, app: CounterApp | None = None) -> None:
        self.config = config or ServiceConfig()
        self.app = app or CounterApp()
        self._stopping = threading.Event()
        self._slots = threading.BoundedSemaphore(self.config.max_connections)
        self._lock = threading.Lock()
        self._connections: set[socket.socket] = set()
        self._threads: set[threading.Thread] = set()
        self._listener: socket.socket | None = None
        self._acceptor: threading.Thread | None = None
        self._address: tuple[str, int] | None = None

    @property
    def address(self) -> tuple[str, int]:
        if self._address is None:
            raise RuntimeError("server has not started")
        return self._address

    @property
    def worker_thread_count(self) -> int:
        with self._lock:
            return len(self._threads)

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
        self._acceptor = threading.Thread(target=self._accept, name="http-acceptor", daemon=True)
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
            if not self._slots.acquire(blocking=False):
                try:
                    connection.sendall(unavailable_response())
                except OSError:
                    pass
                connection.close()
                continue
            thread = threading.Thread(
                target=self._serve, args=(connection,), name="http-connection", daemon=True
            )
            with self._lock:
                self._connections.add(connection)
                self._threads.add(thread)
            thread.start()

    def _serve(self, connection: socket.socket) -> None:
        current = threading.current_thread()
        try:
            with connection:
                serve_connection(connection, self.app, self.config, self._stopping)
        finally:
            with self._lock:
                self._connections.discard(connection)
                self._threads.discard(current)
            self._slots.release()

    def close(self) -> None:
        if self._listener is None:
            return
        deadline = time.monotonic() + self.config.shutdown_timeout
        self._stopping.set()
        self._listener.close()
        if self._acceptor is not None:
            self._acceptor.join(timeout=max(0.0, deadline - time.monotonic()))
        with self._lock:
            connections = list(self._connections)
            threads = list(self._threads)
        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        for thread in threads:
            thread.join(timeout=max(0.0, deadline - time.monotonic()))
        acceptor_alive = self._acceptor is not None and self._acceptor.is_alive()
        live_threads = [thread.name for thread in threads if thread.is_alive()]
        self._listener = None
        if acceptor_alive or live_threads:
            raise RuntimeError(
                "server did not stop within configured shutdown_timeout; "
                f"acceptor_alive={acceptor_alive} live_threads={live_threads!r}"
            )

    def __enter__(self) -> "Server":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
