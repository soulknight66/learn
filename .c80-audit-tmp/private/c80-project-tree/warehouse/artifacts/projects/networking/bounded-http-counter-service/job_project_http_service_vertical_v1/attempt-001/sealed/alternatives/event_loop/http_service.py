from __future__ import annotations

import selectors
import socket
import threading
import time
from dataclasses import dataclass, field

from http_core import (
    CounterApp,
    HTTPParser,
    ProtocolError,
    Request,
    Response,
    ServiceConfig,
    dispatch,
    protocol_error_response,
    serialize_response,
    unavailable_response,
)


ARCHITECTURE = "single-threaded-selector-loop"


@dataclass(eq=False)
class _Connection:
    socket: socket.socket
    parser: HTTPParser
    output: bytearray = field(default_factory=bytearray)
    requests: int = 0
    close_after_write: bool = False
    last_activity: float = field(default_factory=time.monotonic)


class Server:
    def __init__(self, config: ServiceConfig | None = None, app: CounterApp | None = None) -> None:
        self.config = config or ServiceConfig()
        self.app = app or CounterApp()
        self._stopping = threading.Event()
        self._selector: selectors.BaseSelector | None = None
        self._listener: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._states: set[_Connection] = set()
        self._address: tuple[str, int] | None = None

    @property
    def address(self) -> tuple[str, int]:
        if self._address is None:
            raise RuntimeError("server has not started")
        return self._address

    @property
    def worker_thread_count(self) -> int:
        return 1 if self._thread is not None else 0

    def start(self) -> None:
        if self._listener is not None:
            raise RuntimeError("server already started")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.config.host, self.config.port))
        listener.listen(self.config.backlog)
        listener.setblocking(False)
        selector = selectors.DefaultSelector()
        selector.register(listener, selectors.EVENT_READ, None)
        self._listener = listener
        self._selector = selector
        host, port = listener.getsockname()[:2]
        self._address = (str(host), int(port))
        self._thread = threading.Thread(target=self._run, name="http-event-loop", daemon=True)
        self._thread.start()

    def _drop(self, state: _Connection) -> None:
        if state not in self._states:
            return
        self._states.discard(state)
        assert self._selector is not None
        try:
            self._selector.unregister(state.socket)
        except (KeyError, ValueError):
            pass
        state.socket.close()

    def _accept(self) -> None:
        assert self._listener is not None and self._selector is not None
        try:
            connection, _ = self._listener.accept()
        except (BlockingIOError, OSError):
            return
        if len(self._states) >= self.config.max_connections:
            try:
                connection.sendall(unavailable_response())
            except OSError:
                pass
            connection.close()
            return
        connection.setblocking(False)
        state = _Connection(
            connection,
            HTTPParser(self.config.max_header_bytes, self.config.max_body_bytes),
        )
        self._states.add(state)
        self._selector.register(connection, selectors.EVENT_READ, state)

    def _read(self, state: _Connection) -> None:
        assert self._selector is not None
        try:
            data = state.socket.recv(4096)
        except BlockingIOError:
            return
        except OSError:
            self._drop(state)
            return
        if not data:
            self._drop(state)
            return
        state.last_activity = time.monotonic()
        try:
            requests = state.parser.feed(data)
        except ProtocolError as error:
            state.output.extend(protocol_error_response(error))
            state.close_after_write = True
            self._selector.modify(state.socket, selectors.EVENT_WRITE, state)
            return
        for request in requests:
            state.requests += 1
            close = (
                request.headers.get("connection", "").lower() == "close"
                or state.requests >= self.config.max_requests_per_connection
            )
            state.output.extend(serialize_response(dispatch(self.app, request), close=close))
            state.close_after_write = state.close_after_write or close
            if close:
                break
        if state.output:
            self._selector.modify(state.socket, selectors.EVENT_WRITE, state)

    def _write(self, state: _Connection) -> None:
        assert self._selector is not None
        try:
            sent = state.socket.send(state.output)
        except BlockingIOError:
            return
        except OSError:
            self._drop(state)
            return
        del state.output[:sent]
        state.last_activity = time.monotonic()
        if not state.output:
            if state.close_after_write:
                self._drop(state)
            else:
                self._selector.modify(state.socket, selectors.EVENT_READ, state)

    def _run(self) -> None:
        assert self._selector is not None
        while not self._stopping.is_set():
            for key, mask in self._selector.select(0.03):
                state = key.data
                if state is None:
                    self._accept()
                elif mask & selectors.EVENT_READ:
                    self._read(state)
                elif mask & selectors.EVENT_WRITE:
                    self._write(state)
            deadline = time.monotonic() - self.config.read_timeout
            for state in list(self._states):
                if state.last_activity < deadline:
                    self._drop(state)
        for state in list(self._states):
            self._drop(state)

    def close(self) -> None:
        if self._listener is None:
            return
        self._stopping.set()
        self._listener.close()
        if self._thread is not None:
            self._thread.join(timeout=self.config.shutdown_timeout)
            if self._thread.is_alive():
                raise RuntimeError(
                    "event loop did not stop within configured shutdown_timeout"
                )
        if self._selector is not None:
            self._selector.close()
        self._listener = None

    def __enter__(self) -> "Server":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
