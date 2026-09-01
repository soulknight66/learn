from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path
from textwrap import dedent
from typing import Any

from .db import Database
from .util import redact, tree_sha256
from .vertical_slices import SliceResult


_DEFAULT_PROVENANCE = {
    "source_name": "Build Your Own X",
    "source_path": "../build-your-own-x",
    "upstream_url": "https://github.com/codecrafters-io/build-your-own-x",
    "commit_hash": "unknown",
    "license": "CC0-1.0 catalog waiver; linked tutorials retain their licenses",
    "source_reference": "README.md#build-your-own-web-server",
    "external_reference": "catalog entry selected by the ingestion pipeline",
}


def _clean(value: object, *, limit: int = 2_000) -> str:
    return redact(str(value), limit=limit).strip()


def _target(workspace: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or not candidate.parts or any(
        part in {"", ".", ".."} for part in candidate.parts
    ):
        raise ValueError(f"unsafe generated path: {relative!r}")
    root = workspace.resolve()
    path = workspace / candidate
    try:
        path.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError(f"generated path escapes workspace: {relative!r}") from error
    current = workspace
    for part in candidate.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"generated path traverses symlink: {relative!r}")
        current.mkdir(exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"refusing to overwrite symlink: {relative!r}")
    return path


def _write(workspace: Path, relative: str, content: str) -> None:
    rendered = dedent(content).lstrip("\n")
    if rendered and not rendered.endswith("\n"):
        rendered += "\n"
    _target(workspace, relative).write_text(rendered, encoding="utf-8", newline="\n")


def _write_json(workspace: Path, relative: str, value: object) -> None:
    _write(
        workspace,
        relative,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False),
    )


def _provenance(db: Database, payload: dict[str, Any]) -> dict[str, str]:
    """Resolve a small provenance allowlist without archiving arbitrary payload data."""

    result = dict(_DEFAULT_PROVENANCE)
    result["lookup_status"] = "defaults"
    source_id = _clean(payload.get("source_id", ""))
    project_id = _clean(payload.get("project_id", ""))
    row: sqlite3.Row | None = None
    try:
        with db.connect() as connection:
            if project_id:
                row = connection.execute(
                    """
                    SELECT s.source_id,s.name AS source_name,s.path AS source_path,
                           s.upstream_url,s.commit_hash,s.license,
                           p.project_id,p.upstream_reference
                    FROM build_projects p JOIN sources s ON s.source_id=p.source_id
                    WHERE p.project_id=? AND s.is_active=1
                    """,
                    (project_id,),
                ).fetchone()
            elif source_id:
                row = connection.execute(
                    """
                    SELECT source_id,name AS source_name,path AS source_path,
                           upstream_url,commit_hash,license,
                           NULL AS project_id,NULL AS upstream_reference
                    FROM sources WHERE source_id=? AND is_active=1
                    """,
                    (source_id,),
                ).fetchone()
    except sqlite3.Error as error:
        result["lookup_status"] = f"database lookup unavailable: {_clean(error, limit=300)}"
    if row is not None:
        for key in (
            "source_name",
            "source_path",
            "upstream_url",
            "commit_hash",
            "license",
        ):
            if row[key] is not None:
                result[key] = _clean(row[key])
        result["source_id"] = _clean(row["source_id"])
        if row["project_id"] is not None:
            result["project_id"] = _clean(row["project_id"])
        if row["upstream_reference"] is not None:
            result["external_reference"] = _clean(row["upstream_reference"])
        result["lookup_status"] = "database"

    supplied = payload.get("provenance")
    if isinstance(supplied, dict):
        aliases = {
            "source": "source_name",
            "source_id": "source_id",
            "commit": "commit_hash",
            "upstream": "upstream_url",
            "license": "license",
            "catalog_license": "license",
            "catalog_entry": "external_reference",
            "source_reference": "source_reference",
        }
        for incoming, outgoing in aliases.items():
            if supplied.get(incoming):
                result[outgoing] = _clean(supplied[incoming])
        result["lookup_status"] = "job provenance"
    supplied_source = payload.get("source")
    if isinstance(supplied_source, dict):
        aliases = {
            "name": "source_name",
            "path": "source_path",
            "upstream_url": "upstream_url",
            "commit_hash": "commit_hash",
            "license": "license",
            "source_reference": "source_reference",
            "external_reference": "external_reference",
        }
        for incoming, outgoing in aliases.items():
            if supplied_source.get(incoming):
                result[outgoing] = _clean(supplied_source[incoming])
        result["lookup_status"] = "payload source"
    if payload.get("upstream_reference"):
        result["external_reference"] = _clean(payload["upstream_reference"])
    if payload.get("job_id"):
        result["job_id"] = _clean(payload["job_id"])
    return result


_HTTP_CORE = r'''
    from __future__ import annotations

    import json
    import re
    import socket
    import threading
    from collections import OrderedDict
    from dataclasses import dataclass
    from typing import Callable
    from urllib.parse import unquote


    _TOKEN = re.compile(rb"[!#$%&'*+\-.^_`|~0-9A-Za-z]+\Z")
    _NAME = re.compile(r"[a-z][a-z0-9_-]{0,31}\Z")
    _REASONS = {
        200: "OK",
        201: "Created",
        204: "No Content",
        400: "Bad Request",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        411: "Length Required",
        413: "Content Too Large",
        415: "Unsupported Media Type",
        422: "Unprocessable Content",
        431: "Request Header Fields Too Large",
        500: "Internal Server Error",
        503: "Service Unavailable",
        505: "HTTP Version Not Supported",
    }


    @dataclass(frozen=True)
    class ServiceConfig:
        host: str = "127.0.0.1"
        port: int = 0
        worker_count: int = 4
        queue_size: int = 16
        max_connections: int = 32
        backlog: int = 64
        max_header_bytes: int = 8192
        max_body_bytes: int = 65536
        read_timeout: float = 0.5
        shutdown_timeout: float = 2.0
        max_requests_per_connection: int = 20

        def __post_init__(self) -> None:
            if self.host not in {"127.0.0.1", "localhost"}:
                raise ValueError("this teaching service is loopback-only")
            integers = {
                "worker_count": self.worker_count,
                "queue_size": self.queue_size,
                "max_connections": self.max_connections,
                "backlog": self.backlog,
                "max_header_bytes": self.max_header_bytes,
                "max_body_bytes": self.max_body_bytes,
                "max_requests_per_connection": self.max_requests_per_connection,
            }
            if any(value < 1 for value in integers.values()):
                raise ValueError("all capacity limits must be positive")
            if not 0.02 <= self.read_timeout <= 30.0:
                raise ValueError("read_timeout must be between 0.02 and 30 seconds")
            if not 0.1 <= self.shutdown_timeout <= 30.0:
                raise ValueError("shutdown_timeout must be between 0.1 and 30 seconds")


    @dataclass(frozen=True)
    class Request:
        method: str
        target: str
        version: str
        headers: dict[str, str]
        body: bytes


    @dataclass(frozen=True)
    class Response:
        status: int
        headers: dict[str, str]
        body: bytes = b""


    class ProtocolError(ValueError):
        def __init__(self, status: int, message: str) -> None:
            super().__init__(message)
            self.status = status
            self.message = message


    class HTTPParser:
        """Strict, incremental parser for a deliberately small HTTP/1.1 request subset."""

        def __init__(self, max_header_bytes: int = 8192, max_body_bytes: int = 65536) -> None:
            self.max_header_bytes = max_header_bytes
            self.max_body_bytes = max_body_bytes
            self._buffer = bytearray()

        @property
        def buffered_bytes(self) -> int:
            return len(self._buffer)

        def feed(self, data: bytes) -> list[Request]:
            if not isinstance(data, bytes):
                raise TypeError("parser input must be bytes")
            self._buffer.extend(data)
            requests: list[Request] = []
            while True:
                marker = self._buffer.find(b"\r\n\r\n")
                if marker < 0:
                    if len(self._buffer) > self.max_header_bytes:
                        raise ProtocolError(431, "header section exceeds configured limit")
                    if b"\n\n" in self._buffer or b"\r\r" in self._buffer:
                        raise ProtocolError(400, "HTTP lines must use CRLF")
                    return requests
                header_end = marker + 4
                if header_end > self.max_header_bytes:
                    raise ProtocolError(431, "header section exceeds configured limit")
                request_head = bytes(self._buffer[:marker])
                lines = request_head.split(b"\r\n")
                if not lines or len(lines[0].split(b" ")) != 3:
                    raise ProtocolError(400, "malformed request line")
                method_raw, target_raw, version_raw = lines[0].split(b" ")
                if not _TOKEN.fullmatch(method_raw):
                    raise ProtocolError(400, "invalid method token")
                if version_raw != b"HTTP/1.1":
                    raise ProtocolError(505, "only HTTP/1.1 is supported")
                if not target_raw.startswith(b"/") or b"#" in target_raw:
                    raise ProtocolError(400, "only origin-form request targets are supported")
                try:
                    method = method_raw.decode("ascii")
                    target = target_raw.decode("ascii")
                except UnicodeDecodeError as error:
                    raise ProtocolError(400, "request line must be ASCII") from error
                headers: dict[str, str] = {}
                for line in lines[1:]:
                    if line.startswith((b" ", b"\t")) or b":" not in line:
                        raise ProtocolError(400, "malformed or folded header")
                    name_raw, value_raw = line.split(b":", 1)
                    if not _TOKEN.fullmatch(name_raw):
                        raise ProtocolError(400, "invalid header name")
                    try:
                        name = name_raw.decode("ascii").lower()
                        value = value_raw.decode("latin-1").strip(" \t")
                    except UnicodeDecodeError as error:
                        raise ProtocolError(400, "invalid header encoding") from error
                    if "\x00" in value or "\r" in value or "\n" in value:
                        raise ProtocolError(400, "invalid header value")
                    if name in headers:
                        raise ProtocolError(400, f"duplicate header is not accepted: {name}")
                    headers[name] = value
                if "host" not in headers or not headers["host"]:
                    raise ProtocolError(400, "HTTP/1.1 Host header is required")
                if "transfer-encoding" in headers:
                    raise ProtocolError(400, "Transfer-Encoding is outside this service contract")
                content_length = headers.get("content-length", "0")
                if not content_length.isascii() or not content_length.isdecimal():
                    raise ProtocolError(400, "Content-Length must be decimal")
                length = int(content_length)
                if length > self.max_body_bytes:
                    raise ProtocolError(413, "request body exceeds configured limit")
                if len(self._buffer) < header_end + length:
                    return requests
                body = bytes(self._buffer[header_end : header_end + length])
                del self._buffer[: header_end + length]
                requests.append(Request(method, target, "HTTP/1.1", headers, body))


    def json_response(status: int, value: object, **headers: str) -> Response:
        body = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return Response(status, {"content-type": "application/json", **headers}, body)


    class CounterApp:
        """Thread-safe application with bounded in-memory idempotency evidence and metrics."""

        def __init__(
            self,
            *,
            idempotency_capacity: int = 256,
            fault_hook: Callable[[Request], None] | None = None,
        ) -> None:
            if idempotency_capacity < 1:
                raise ValueError("idempotency_capacity must be positive")
            self._values: dict[str, tuple[int, int]] = {}
            self._idempotency: OrderedDict[
                str, tuple[tuple[str, int], Response]
            ] = OrderedDict()
            self._idempotency_capacity = idempotency_capacity
            self._fault_hook = fault_hook
            self._metrics: dict[str, int] = {
                "requests_total": 0,
                "application_errors_total": 0,
            }
            self._lock = threading.RLock()

        def _decode_name(self, raw: str) -> str | None:
            try:
                value = unquote(raw, errors="strict")
            except UnicodeDecodeError:
                return None
            return value if _NAME.fullmatch(value) else None

        def _payload(self, request: Request, required: str) -> tuple[int | None, Response | None]:
            if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
                return None, json_response(415, {"error": "content-type must be application/json"})
            try:
                value = json.loads(request.body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None, json_response(400, {"error": "body must be valid UTF-8 JSON"})
            if not isinstance(value, dict) or set(value) != {required}:
                return None, json_response(422, {"error": f"body must contain only {required!r}"})
            number = value[required]
            if isinstance(number, bool) or not isinstance(number, int) or abs(number) > 10**12:
                return None, json_response(422, {"error": f"{required} must be a bounded integer"})
            return number, None

        def handle(self, request: Request) -> Response:
            if self._fault_hook is not None:
                self._fault_hook(request)
            with self._lock:
                self._metrics["requests_total"] += 1
                path = request.target.split("?", 1)[0]
                if path == "/healthz" and request.method == "GET":
                    return json_response(200, {"status": "ok"})
                if path == "/metrics" and request.method == "GET":
                    lines = [
                        f"counter_service_{name} {value}"
                        for name, value in sorted(self._metrics.items())
                    ]
                    body = ("\n".join(lines) + "\n").encode("ascii")
                    return Response(200, {"content-type": "text/plain; version=0.0.4"}, body)
                prefix = "/v1/counters/"
                if not path.startswith(prefix):
                    return json_response(404, {"error": "route not found"})
                suffix = path[len(prefix) :]
                increment = suffix.endswith("/increment")
                raw_name = suffix[: -len("/increment")] if increment else suffix
                name = self._decode_name(raw_name)
                if name is None:
                    return json_response(404, {"error": "counter name is invalid"})

                if increment:
                    if request.method != "POST":
                        return json_response(405, {"error": "method not allowed"}, allow="POST")
                    if "content-length" not in request.headers:
                        return json_response(411, {"error": "Content-Length is required"})
                    key = request.headers.get("idempotency-key")
                    if key is not None:
                        if not 1 <= len(key) <= 80 or any(ord(char) < 33 or ord(char) > 126 for char in key):
                            return json_response(400, {"error": "invalid Idempotency-Key"})
                    delta, error = self._payload(request, "delta")
                    if error is not None:
                        return error
                    assert delta is not None
                    operation = (name, delta)
                    if key is not None:
                        cached = self._idempotency.get(key)
                        if cached is not None:
                            cached_operation, cached_response = cached
                            if cached_operation != operation:
                                return json_response(
                                    409,
                                    {"error": "Idempotency-Key was already used for another operation"},
                                )
                            self._idempotency.move_to_end(key)
                            return cached_response
                    old_value, old_version = self._values.get(name, (0, 0))
                    response = json_response(
                        200,
                        {"name": name, "value": old_value + delta, "version": old_version + 1},
                        etag=f'"{old_version + 1}"',
                    )
                    self._values[name] = (old_value + delta, old_version + 1)
                    if key is not None:
                        self._idempotency[key] = (operation, response)
                        while len(self._idempotency) > self._idempotency_capacity:
                            self._idempotency.popitem(last=False)
                    return response

                if request.method == "GET":
                    if name not in self._values:
                        return json_response(404, {"error": "counter not found"})
                    value, version = self._values[name]
                    return json_response(
                        200,
                        {"name": name, "value": value, "version": version},
                        etag=f'"{version}"',
                    )
                if request.method == "PUT":
                    if "content-length" not in request.headers:
                        return json_response(411, {"error": "Content-Length is required"})
                    value, error = self._payload(request, "value")
                    if error is not None:
                        return error
                    assert value is not None
                    existed = name in self._values
                    _, version = self._values.get(name, (0, 0))
                    expected = request.headers.get("if-match")
                    if expected is not None and expected != f'"{version}"':
                        return json_response(409, {"error": "version conflict", "version": version})
                    self._values[name] = (value, version + 1)
                    return json_response(
                        200 if existed else 201,
                        {"name": name, "value": value, "version": version + 1},
                        etag=f'"{version + 1}"',
                    )
                if request.method == "DELETE":
                    if name not in self._values:
                        return json_response(404, {"error": "counter not found"})
                    del self._values[name]
                    return Response(204, {})
                return json_response(405, {"error": "method not allowed"}, allow="GET, PUT, DELETE")

        def record_application_error(self) -> None:
            with self._lock:
                self._metrics["application_errors_total"] += 1


    def serialize_response(response: Response, *, close: bool) -> bytes:
        reason = _REASONS.get(response.status, "Unknown")
        headers = {key.lower(): value for key, value in response.headers.items()}
        headers["content-length"] = str(len(response.body))
        headers["connection"] = "close" if close else "keep-alive"
        if "content-type" not in headers and response.body:
            headers["content-type"] = "application/octet-stream"
        lines = [f"HTTP/1.1 {response.status} {reason}\r\n"]
        lines.extend(f"{name}: {value}\r\n" for name, value in sorted(headers.items()))
        return ("".join(lines) + "\r\n").encode("latin-1") + response.body


    def unavailable_response() -> bytes:
        return serialize_response(
            json_response(503, {"error": "connection capacity exhausted"}), close=True
        )


    def dispatch(app: CounterApp, request: Request) -> Response:
        try:
            return app.handle(request)
        except Exception:
            app.record_application_error()
            return json_response(500, {"error": "internal server error"})


    def protocol_error_response(error: ProtocolError) -> bytes:
        return serialize_response(json_response(error.status, {"error": error.message}), close=True)


    def serve_connection(
        connection: socket.socket,
        app: CounterApp,
        config: ServiceConfig,
        stopping: threading.Event,
    ) -> None:
        connection.settimeout(config.read_timeout)
        parser = HTTPParser(config.max_header_bytes, config.max_body_bytes)
        completed = 0
        while not stopping.is_set() and completed < config.max_requests_per_connection:
            try:
                chunk = connection.recv(4096)
            except (socket.timeout, ConnectionError, OSError):
                return
            if not chunk:
                return
            try:
                requests = parser.feed(chunk)
            except ProtocolError as error:
                try:
                    connection.sendall(protocol_error_response(error))
                except OSError:
                    pass
                return
            for request in requests:
                completed += 1
                close = (
                    request.headers.get("connection", "").lower() == "close"
                    or completed >= config.max_requests_per_connection
                )
                try:
                    connection.sendall(serialize_response(dispatch(app, request), close=close))
                except OSError:
                    return
                if close:
                    return
'''


_WORKER_POOL = r'''
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
'''


_THREAD_PER_CONNECTION = r'''
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
'''


_EVENT_LOOP = r'''
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
    '''


_PUBLIC_TESTS = r'''
    from __future__ import annotations

    import json
    import socket
    import unittest

    from http_service import CounterApp, HTTPParser, Request, Server, ServiceConfig


    def request_bytes(
        method: str,
        target: str,
        body: bytes = b"",
        *,
        headers: dict[str, str] | None = None,
        close: bool = True,
    ) -> bytes:
        values = {"Host": "exercise.local", **(headers or {})}
        if body or method in {"PUT", "POST"}:
            values.setdefault("Content-Length", str(len(body)))
        values["Connection"] = "close" if close else "keep-alive"
        head = f"{method} {target} HTTP/1.1\r\n" + "".join(
            f"{name}: {value}\r\n" for name, value in values.items()
        )
        return head.encode("ascii") + b"\r\n" + body


    def exchange(address: tuple[str, int], payload: bytes) -> bytes:
        with socket.create_connection(address, timeout=2.0) as client:
            client.settimeout(2.0)
            client.sendall(payload)
            chunks: list[bytes] = []
            while True:
                data = client.recv(65536)
                if not data:
                    return b"".join(chunks)
                chunks.append(data)


    def response_json(raw: bytes) -> tuple[int, dict[str, str], object]:
        head, body = raw.split(b"\r\n\r\n", 1)
        lines = head.decode("latin-1").split("\r\n")
        status = int(lines[0].split(" ", 2)[1])
        headers = {name.lower(): value.strip() for name, value in (
            line.split(":", 1) for line in lines[1:]
        )}
        assert int(headers["content-length"]) == len(body)
        return status, headers, json.loads(body) if body else None


    class PublicParserTests(unittest.TestCase):
        def test_fragmented_request_is_not_emitted_early(self) -> None:
            parser = HTTPParser()
            wire = request_bytes("PUT", "/v1/counters/jobs", b'{"value":7}', headers={"Content-Type": "application/json"})
            observed = []
            for byte in wire:
                observed.extend(parser.feed(bytes([byte])))
            self.assertEqual(1, len(observed))
            self.assertEqual(b'{"value":7}', observed[0].body)

        def test_two_pipelined_requests_are_preserved(self) -> None:
            parser = HTTPParser()
            requests = parser.feed(
                request_bytes("GET", "/healthz", close=False)
                + request_bytes("GET", "/metrics")
            )
            self.assertEqual(["/healthz", "/metrics"], [item.target for item in requests])


    class PublicApplicationTests(unittest.TestCase):
        def test_idempotent_increment_is_applied_once(self) -> None:
            app = CounterApp()
            request = Request(
                "POST",
                "/v1/counters/builds/increment",
                "HTTP/1.1",
                {
                    "host": "exercise.local",
                    "content-length": "11",
                    "content-type": "application/json",
                    "idempotency-key": "build-42",
                },
                b'{"delta":3}',
            )
            first = app.handle(request)
            second = app.handle(request)
            self.assertEqual(first, second)
            fetched = app.handle(Request("GET", "/v1/counters/builds", "HTTP/1.1", {"host": "exercise.local"}, b""))
            self.assertEqual(3, json.loads(fetched.body)["value"])


    class PublicNetworkTests(unittest.TestCase):
        def setUp(self) -> None:
            self.server = Server(ServiceConfig(worker_count=2, read_timeout=0.2))
            self.server.start()

        def tearDown(self) -> None:
            self.server.close()

        def test_health_endpoint(self) -> None:
            status, headers, body = response_json(
                exchange(self.server.address, request_bytes("GET", "/healthz"))
            )
            self.assertEqual(200, status)
            self.assertEqual("close", headers["connection"])
            self.assertEqual({"status": "ok"}, body)

        def test_put_then_get_exposes_version(self) -> None:
            status, _, created = response_json(
                exchange(
                    self.server.address,
                    request_bytes(
                        "PUT",
                        "/v1/counters/releases",
                        b'{"value":9}',
                        headers={"Content-Type": "application/json"},
                    ),
                )
            )
            self.assertEqual(201, status)
            self.assertEqual(1, created["version"])
            status, headers, fetched = response_json(
                exchange(self.server.address, request_bytes("GET", "/v1/counters/releases"))
            )
            self.assertEqual(200, status)
            self.assertEqual('"1"', headers["etag"])
            self.assertEqual(9, fetched["value"])


    if __name__ == "__main__":
        unittest.main()
'''


_HIDDEN_TESTS = r'''
    from __future__ import annotations

    import json
    import socket
    import threading
    import time
    import unittest

    from http_service import HTTPParser, ProtocolError, Server, ServiceConfig


    def wire(
        method: str,
        target: str,
        body: bytes = b"",
        *,
        headers: dict[str, str] | None = None,
        close: bool = True,
    ) -> bytes:
        values = {"Host": "hidden.local", **(headers or {})}
        if body or method in {"PUT", "POST"}:
            values.setdefault("Content-Length", str(len(body)))
        values["Connection"] = "close" if close else "keep-alive"
        return (
            f"{method} {target} HTTP/1.1\r\n"
            + "".join(f"{key}: {value}\r\n" for key, value in values.items())
            + "\r\n"
        ).encode("ascii") + body


    def exchange(address: tuple[str, int], payload: bytes) -> bytes:
        with socket.create_connection(address, timeout=2.0) as client:
            client.settimeout(2.0)
            client.sendall(payload)
            output = bytearray()
            while True:
                chunk = client.recv(65536)
                if not chunk:
                    return bytes(output)
                output.extend(chunk)


    def parse_one(raw: bytes) -> tuple[int, dict[str, str], object]:
        head, body = raw.split(b"\r\n\r\n", 1)
        lines = head.decode("latin-1").split("\r\n")
        status = int(lines[0].split(" ", 2)[1])
        headers = dict(line.split(": ", 1) for line in lines[1:])
        return status, headers, json.loads(body) if body else None


    def read_one(client: socket.socket) -> bytes:
        raw = bytearray()
        while b"\r\n\r\n" not in raw:
            chunk = client.recv(65536)
            if not chunk:
                raise AssertionError("connection closed before response headers")
            raw.extend(chunk)
        marker = raw.index(b"\r\n\r\n") + 4
        head = bytes(raw[: marker - 4]).decode("latin-1")
        headers = dict(line.split(": ", 1) for line in head.split("\r\n")[1:])
        expected = marker + int(headers["content-length"])
        while len(raw) < expected:
            chunk = client.recv(65536)
            if not chunk:
                raise AssertionError("connection closed before response body")
            raw.extend(chunk)
        return bytes(raw[:expected])


    class HiddenParserTests(unittest.TestCase):
        def assert_protocol_status(self, payload: bytes, status: int) -> None:
            with self.assertRaises(ProtocolError) as caught:
                HTTPParser(max_header_bytes=256, max_body_bytes=16).feed(payload)
            self.assertEqual(status, caught.exception.status)

        def test_missing_host_is_rejected(self) -> None:
            self.assert_protocol_status(b"GET / HTTP/1.1\r\n\r\n", 400)

        def test_duplicate_content_length_is_rejected(self) -> None:
            self.assert_protocol_status(
                b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 1\r\nContent-Length: 2\r\n\r\nx",
                400,
            )

        def test_transfer_encoding_is_rejected(self) -> None:
            self.assert_protocol_status(
                b"POST / HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n",
                400,
            )

        def test_oversized_body_is_rejected_before_body_arrives(self) -> None:
            self.assert_protocol_status(
                b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 99\r\n\r\n",
                413,
            )

        def test_bare_newline_termination_is_rejected(self) -> None:
            self.assert_protocol_status(b"GET / HTTP/1.1\nHost: x\n\n", 400)


    class HiddenNetworkContractTests(unittest.TestCase):
        def setUp(self) -> None:
            self.server = Server(
                ServiceConfig(
                    worker_count=4,
                    queue_size=8,
                    max_connections=16,
                    read_timeout=0.25,
                )
            )
            self.server.start()

        def tearDown(self) -> None:
            self.server.close()

        def test_pipelining_writes_two_complete_responses(self) -> None:
            raw = exchange(
                self.server.address,
                wire("GET", "/healthz", close=False) + wire("GET", "/healthz"),
            )
            self.assertEqual(2, raw.count(b"HTTP/1.1 200 OK"))
            self.assertTrue(raw.endswith(b'{"status":"ok"}'))

        def test_request_budget_stops_pipelined_dispatch(self) -> None:
            self.server.close()
            self.server = Server(
                ServiceConfig(
                    worker_count=2,
                    queue_size=2,
                    max_connections=2,
                    read_timeout=0.25,
                    max_requests_per_connection=1,
                )
            )
            self.server.start()
            raw = exchange(
                self.server.address,
                wire("GET", "/healthz", close=False) + wire("GET", "/healthz"),
            )
            self.assertEqual(1, raw.count(b"HTTP/1.1 200 OK"))

        def test_compare_and_set_conflict_does_not_mutate(self) -> None:
            create = wire(
                "PUT",
                "/v1/counters/deploys",
                b'{"value":2}',
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(201, parse_one(exchange(self.server.address, create))[0])
            conflict = wire(
                "PUT",
                "/v1/counters/deploys",
                b'{"value":8}',
                headers={"Content-Type": "application/json", "If-Match": '"0"'},
            )
            self.assertEqual(409, parse_one(exchange(self.server.address, conflict))[0])
            _, _, body = parse_one(
                exchange(self.server.address, wire("GET", "/v1/counters/deploys"))
            )
            self.assertEqual(2, body["value"])

        def test_idempotency_key_conflict_cannot_cross_resources(self) -> None:
            first = wire(
                "POST",
                "/v1/counters/alpha/increment",
                b'{"delta":1}',
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": "shared-operation-key",
                },
            )
            self.assertEqual(200, parse_one(exchange(self.server.address, first))[0])
            conflict = wire(
                "POST",
                "/v1/counters/beta/increment",
                b'{"delta":1}',
                headers={
                    "Content-Type": "application/json",
                    "Idempotency-Key": "shared-operation-key",
                },
            )
            status, _, body = parse_one(exchange(self.server.address, conflict))
            self.assertEqual(409, status)
            self.assertIn("another operation", body["error"])
            self.assertEqual(
                404,
                parse_one(
                    exchange(self.server.address, wire("GET", "/v1/counters/beta"))
                )[0],
            )

        def test_close_unblocks_idle_keepalive_before_read_timeout(self) -> None:
            self.server.close()
            self.server = Server(
                ServiceConfig(
                    worker_count=2,
                    queue_size=2,
                    max_connections=2,
                    read_timeout=3.0,
                    shutdown_timeout=0.75,
                )
            )
            self.server.start()
            with socket.create_connection(self.server.address, timeout=2.0) as client:
                client.settimeout(2.0)
                client.sendall(wire("GET", "/healthz", close=False))
                self.assertTrue(read_one(client).startswith(b"HTTP/1.1 200 OK"))
                started = time.monotonic()
                self.server.close()
                elapsed = time.monotonic() - started
            self.assertLess(elapsed, 1.5)

        def test_concurrent_unique_increments_are_not_lost(self) -> None:
            failures: list[BaseException] = []

            def increment(worker: int) -> None:
                try:
                    for step in range(15):
                        request = wire(
                            "POST",
                            "/v1/counters/parallel/increment",
                            b'{"delta":1}',
                            headers={
                                "Content-Type": "application/json",
                                "Idempotency-Key": f"{worker}-{step}",
                            },
                        )
                        if parse_one(exchange(self.server.address, request))[0] != 200:
                            raise AssertionError("increment failed")
                except BaseException as error:
                    failures.append(error)

            threads = [threading.Thread(target=increment, args=(worker,)) for worker in range(6)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            if failures:
                raise failures[0]
            _, _, body = parse_one(
                exchange(self.server.address, wire("GET", "/v1/counters/parallel"))
            )
            self.assertEqual(90, body["value"])

        def test_malformed_protocol_gets_structured_error(self) -> None:
            status, headers, body = parse_one(
                exchange(self.server.address, b"GET / HTTP/1.1\r\n\r\n")
            )
            self.assertEqual(400, status)
            self.assertEqual("close", headers["connection"])
            self.assertIn("error", body)


    if __name__ == "__main__":
        unittest.main()
'''


_PARSER_ADVERSARY = r'''
    from __future__ import annotations

    import argparse
    import random

    from http_service import HTTPParser, ProtocolError


    VALID = b"PUT /v1/counters/parser HTTP/1.1\r\nHost: fuzz.local\r\nContent-Type: application/json\r\nContent-Length: 12\r\n\r\n{\"value\":41}"


    def main() -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("--seed", type=int, default=20260830)
        parser.add_argument("--iterations", type=int, default=120)
        args = parser.parse_args()
        if args.iterations < 1 or args.iterations > 2000:
            parser.error("iterations must be between 1 and 2000")
        randomizer = random.Random(args.seed)
        for _ in range(args.iterations):
            subject = HTTPParser(max_header_bytes=512, max_body_bytes=64)
            cursor = 0
            requests = []
            while cursor < len(VALID):
                width = randomizer.randint(1, 9)
                requests.extend(subject.feed(VALID[cursor : cursor + width]))
                cursor += width
            assert len(requests) == 1 and requests[0].body == b'{"value":41}'
        invalid = [
            b"GET / HTTP/1.1\r\n\r\n",
            b"GET / HTTP/1.0\r\nHost: x\r\n\r\n",
            b"GET / HTTP/1.1\r\nHost: x\r\nHost: y\r\n\r\n",
            b"GET / HTTP/1.1\r\n Host: x\r\n\r\n",
            b"POST / HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n",
            b"POST / HTTP/1.1\r\nHost: x\r\nContent-Length: +1\r\n\r\nx",
        ]
        for payload in invalid:
            try:
                HTTPParser().feed(payload)
            except ProtocolError:
                pass
            else:
                raise AssertionError(f"invalid request accepted: {payload!r}")
        print(f"parser adversary passed seed={args.seed} iterations={args.iterations}")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_FAULT_CHECK = r'''
    from __future__ import annotations

    import socket

    from http_service import CounterApp, Server, ServiceConfig


    def exchange(address: tuple[str, int], target: str) -> bytes:
        request = (
            f"GET {target} HTTP/1.1\r\nHost: fault.local\r\nConnection: close\r\n\r\n"
        ).encode("ascii")
        with socket.create_connection(address, timeout=2.0) as client:
            client.settimeout(2.0)
            client.sendall(request)
            output = bytearray()
            while True:
                chunk = client.recv(65536)
                if not chunk:
                    return bytes(output)
                output.extend(chunk)


    def inject(request: object) -> None:
        if getattr(request, "target") == "/fault":
            raise RuntimeError("sensitive backend detail that must not escape")


    def main() -> int:
        with Server(
            ServiceConfig(worker_count=2, read_timeout=0.2),
            CounterApp(fault_hook=inject),
        ) as server:
            failed = exchange(server.address, "/fault")
            assert failed.startswith(b"HTTP/1.1 500 Internal Server Error")
            assert b"sensitive backend detail" not in failed
            healthy = exchange(server.address, "/healthz")
            assert healthy.startswith(b"HTTP/1.1 200 OK")
            metrics = exchange(server.address, "/metrics")
            assert b"counter_service_application_errors_total 1" in metrics
        print("application fault was contained and the service remained healthy")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_SLOW_CLIENT_CHECK = r'''
    from __future__ import annotations

    import socket
    import time

    from http_service import Server, ServiceConfig


    def main() -> int:
        config = ServiceConfig(worker_count=2, queue_size=2, read_timeout=0.12)
        with Server(config) as server:
            slow = [socket.create_connection(server.address, timeout=1.0) for _ in range(2)]
            try:
                for client in slow:
                    client.sendall(b"GET /healthz HTTP/1.1\r\nHost: slow.local\r\nX-Padding: ")
                assert server.worker_thread_count <= max(config.worker_count, config.max_connections)
                time.sleep(0.3)
                request = b"GET /healthz HTTP/1.1\r\nHost: slow.local\r\nConnection: close\r\n\r\n"
                with socket.create_connection(server.address, timeout=1.0) as probe:
                    probe.settimeout(1.0)
                    probe.sendall(request)
                    response = bytearray()
                    while True:
                        chunk = probe.recv(65536)
                        if not chunk:
                            break
                        response.extend(chunk)
                assert bytes(response).startswith(b"HTTP/1.1 200 OK"), response
            finally:
                for client in slow:
                    client.close()
        print("slow partial headers timed out and bounded capacity recovered")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
    '''


_BENCHMARK = r'''
    from __future__ import annotations

    import argparse
    import importlib.util
    import json
    import os
    import platform
    import socket
    import statistics
    import sys
    import time
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    from types import ModuleType


    ROOT = Path(__file__).resolve().parents[1]
    SHARED = ROOT / "sealed/shared"
    IMPLEMENTATIONS = {
        "worker_pool": ROOT / "sealed/reference/http_service.py",
        "thread_per_connection": ROOT / "sealed/alternatives/thread_per_connection/http_service.py",
        "event_loop": ROOT / "sealed/alternatives/event_loop/http_service.py",
    }


    def load(name: str, path: Path) -> ModuleType:
        if str(SHARED) not in sys.path:
            sys.path.insert(0, str(SHARED))
        spec = importlib.util.spec_from_file_location(f"bench_{name}", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import implementation: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


    REQUEST = b"GET /healthz HTTP/1.1\r\nHost: benchmark.local\r\nConnection: close\r\n\r\n"


    def one_request(address: tuple[str, int]) -> int:
        started = time.perf_counter_ns()
        with socket.create_connection(address, timeout=2.0) as client:
            client.settimeout(2.0)
            client.sendall(REQUEST)
            response = bytearray()
            while True:
                chunk = client.recv(65536)
                if not chunk:
                    break
                response.extend(chunk)
        if not bytes(response).startswith(b"HTTP/1.1 200 OK"):
            raise RuntimeError(f"benchmark received invalid response: {bytes(response[:100])!r}")
        return time.perf_counter_ns() - started


    def measure(module: ModuleType, requests: int, concurrency: int) -> dict[str, object]:
        config = module.ServiceConfig(
            worker_count=max(2, concurrency),
            queue_size=max(4, concurrency * 2),
            max_connections=max(8, concurrency * 2),
            read_timeout=0.5,
        )
        server = module.Server(config)
        server.start()
        try:
            one_request(server.address)
            sequential_samples = [one_request(server.address) for _ in range(requests)]
            burst_started = time.perf_counter_ns()
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                burst_samples = list(
                    executor.map(lambda _: one_request(server.address), range(requests))
                )
            burst_total = time.perf_counter_ns() - burst_started
        finally:
            server.close()
        return {
            "architecture": module.ARCHITECTURE,
            "sequential_latency_ns_raw": sequential_samples,
            "sequential_median_ns": statistics.median(sequential_samples),
            "sequential_p95_ns": sorted(sequential_samples)[max(0, int(len(sequential_samples) * 0.95) - 1)],
            "burst_latency_ns_raw": burst_samples,
            "burst_total_ns": burst_total,
            "burst_requests_per_second": requests / (burst_total / 1_000_000_000),
        }


    def main() -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("--requests", type=int, default=40)
        parser.add_argument("--concurrency", type=int, default=4)
        parser.add_argument("--output", type=Path, required=True)
        args = parser.parse_args()
        if not 5 <= args.requests <= 500:
            parser.error("requests must be between 5 and 500")
        if not 1 <= args.concurrency <= 32:
            parser.error("concurrency must be between 1 and 32")
        raw_results = {
            name: measure(load(name, path), args.requests, args.concurrency)
            for name, path in IMPLEMENTATIONS.items()
        }
        report = {
            "schema_version": 1,
            "hypothesis": (
                "A bounded worker pool should amortize thread creation, while the selector loop "
                "should stay competitive for tiny nonblocking handlers; this smoke workload is too "
                "small to establish production capacity."
            ),
            "parameters": {
                "requests_per_workload": args.requests,
                "concurrency": args.concurrency,
                "endpoint": "GET /healthz over a new loopback connection",
            },
            "environment": {
                "python": platform.python_version(),
                "implementation": platform.python_implementation(),
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor() or "unreported",
                "cpu_count": os.cpu_count(),
                "timer": "time.perf_counter_ns",
                "network": "IPv4 loopback only",
            },
            "raw_results": raw_results,
            "interpretation_boundary": (
                "Measured values are machine-specific bounded smoke evidence, not a load-test, "
                "capacity promise, or claim of statistical significance."
            ),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            name: round(value["burst_requests_per_second"], 2)
            for name, value in raw_results.items()
        }, sort_keys=True))
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_DEBUG_REGRESSION = r'''
    from __future__ import annotations

    from http_core import HTTPParser


    def main() -> int:
        parser = HTTPParser()
        head = (
            b"PUT /v1/counters/partial HTTP/1.1\r\n"
            b"Host: debug.local\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: 13\r\n\r\n"
        )
        first = parser.feed(head + b'{"val')
        assert first == [], "parser emitted a request before Content-Length bytes arrived"
        second = parser.feed(b'ue":123}')
        assert len(second) == 1
        assert second[0].body == b'{"value":123}'
        print("fragmented body remained buffered until complete")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_REVIEW_CACHE = r'''
    from __future__ import annotations

    import threading

    from http_core import Request, Response


    class ResponseCache:
        """Proposed PR implementation; review before relying on it."""

        def __init__(self, application: object) -> None:
            self.application = application
            self.cache: dict[str, Response] = {}
            self.lock = threading.Lock()

        def handle(self, request: Request) -> Response:
            if request.method != "GET":
                return self.application.handle(request)
            with self.lock:
                if request.target in self.cache:
                    return self.cache[request.target]
                response = self.application.handle(request)
                if response.status == 200:
                    self.cache[request.target] = response
                return response
'''


_REVIEW_DEMONSTRATION = r'''
    from __future__ import annotations

    from cache_layer import ResponseCache
    from http_core import Request, Response


    class AccountApplication:
        def handle(self, request: Request) -> Response:
            identity = request.headers.get("authorization", "anonymous")
            return Response(200, {"content-type": "text/plain"}, f"profile:{identity}".encode())


    def main() -> int:
        cached = ResponseCache(AccountApplication())
        alice = Request("GET", "/v1/me", "HTTP/1.1", {"authorization": "alice"}, b"")
        bob = Request("GET", "/v1/me", "HTTP/1.1", {"authorization": "bob"}, b"")
        alice_response = cached.handle(alice)
        bob_response = cached.handle(bob)
        assert alice_response.body == b"profile:alice"
        assert bob_response.body == b"profile:alice"
        assert bob_response.body != b"profile:bob"
        print("reproduced cross-principal response disclosure caused by the proposed cache key")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_STARTER = r'''
    from __future__ import annotations

    from dataclasses import dataclass


    @dataclass(frozen=True)
    class ServiceConfig:
        host: str = "127.0.0.1"
        port: int = 0
        worker_count: int = 4
        queue_size: int = 16
        max_connections: int = 32
        backlog: int = 64
        max_header_bytes: int = 8192
        max_body_bytes: int = 65536
        read_timeout: float = 0.5
        shutdown_timeout: float = 2.0
        max_requests_per_connection: int = 20


    @dataclass(frozen=True)
    class Request:
        method: str
        target: str
        version: str
        headers: dict[str, str]
        body: bytes


    @dataclass(frozen=True)
    class Response:
        status: int
        headers: dict[str, str]
        body: bytes = b""


    class ProtocolError(ValueError):
        def __init__(self, status: int, message: str) -> None:
            super().__init__(message)
            self.status = status


    class HTTPParser:
        def __init__(self, max_header_bytes: int = 8192, max_body_bytes: int = 65536) -> None:
            raise NotImplementedError("implement the bounded incremental parser")

        def feed(self, data: bytes) -> list[Request]:
            raise NotImplementedError


    class CounterApp:
        def __init__(self, *, idempotency_capacity: int = 256, fault_hook: object = None) -> None:
            raise NotImplementedError("implement the thread-safe counter application")

        def handle(self, request: Request) -> Response:
            raise NotImplementedError


    class Server:
        def __init__(self, config: ServiceConfig | None = None, app: CounterApp | None = None) -> None:
            raise NotImplementedError("implement one bounded concurrency architecture")
'''


_SYNTAX_CHECKER = r'''
    from __future__ import annotations

    import sys
    from pathlib import Path


    def main() -> int:
        failures: list[str] = []
        for path in sorted(Path(".").rglob("*.py")):
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except (OSError, SyntaxError, UnicodeError) as error:
                failures.append(f"{path}: {error}")
        if failures:
            print("\n".join(failures), file=sys.stderr)
            return 1
        print("all generated Python sources compile")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_RUN_ALL = r'''
    from __future__ import annotations

    import os
    import subprocess
    import sys
    from pathlib import Path


    ROOT = Path(__file__).resolve().parents[1]
    SHARED = "sealed/shared"


    def run(label: str, argv: list[str], *, path: str | None = None, expected: int = 0) -> None:
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        if path is not None:
            environment["PYTHONPATH"] = path
        print(f"==> {label}", flush=True)
        completed = subprocess.run(argv, cwd=ROOT, env=environment, check=False)
        if completed.returncode != expected:
            raise SystemExit(
                f"{label} exited {completed.returncode}; expected {expected}"
            )


    def main() -> int:
        implementations = {
            "reference": f"sealed/reference:{SHARED}",
            "thread-per-connection": f"sealed/alternatives/thread_per_connection:{SHARED}",
            "event-loop": f"sealed/alternatives/event_loop:{SHARED}",
        }
        run("syntax", [sys.executable, "environment/check_python.py"])
        for name, path in implementations.items():
            run(f"{name} public contract", [sys.executable, "-m", "unittest", "discover", "-s", "public_tests", "-v"], path=path)
            run(f"{name} hidden contract", [sys.executable, "-m", "unittest", "discover", "-s", "sealed/reference_tests", "-v"], path=path)
        run("parser adversary", [sys.executable, "adversarial/parser/check.py", "--iterations", "120"], path=implementations["reference"])
        run("fault containment", [sys.executable, "adversarial/fault-injection/check.py"], path=implementations["reference"])
        run("slow-client recovery", [sys.executable, "adversarial/slow-client/check.py"], path=implementations["reference"])
        run("bug reproduction", [sys.executable, "debugging/partial-body/regression.py"], path="debugging/partial-body/buggy", expected=1)
        run("debug reference", [sys.executable, "debugging/partial-body/regression.py"], path=SHARED)
        run("review finding reproduction", [sys.executable, "review_exercises/cache-layer/sealed/demonstrate.py"], path=f"review_exercises/cache-layer/proposed:{SHARED}")
        run(
            "bounded benchmark",
            [sys.executable, "benchmarks/benchmark.py", "--requests", "40", "--concurrency", "4", "--output", "benchmarks/results/smoke.json"],
        )
        print("all bounded validation stages behaved as expected")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
    '''


def generate_http_service_slice(
    workspace: Path, payload: dict[str, Any], db: Database
) -> SliceResult:
    """Generate a tested HTTP/1.1 production-engineering challenge pack.

    Generation itself makes no completion claim.  The returned argv validators are
    intended to run in the controller-owned validation phase before promotion.
    """

    if not workspace.is_dir() or workspace.is_symlink():
        raise ValueError("HTTP service workspace must be an existing real directory")
    provenance = _provenance(db, payload)

    _write(
        workspace,
        "README.md",
        """
        # Bounded HTTP Counter Service

        Build a small HTTP/1.1 service without a web framework, then examine why protocol parsing,
        overload behavior, concurrency, lifecycle, and operations matter as much as route code. The
        service stores named integer counters in memory and exposes compare-and-set and idempotent
        increment operations. It is intentionally loopback-only and uses Python 3.11's standard
        library so the engineering mechanisms remain visible.

        This pack was newly generated from a Build Your Own X catalog relationship. No tutorial code
        or prose was copied. `PROVENANCE.json` distinguishes catalog metadata, generated material,
        measured evidence, and inferences.

        ## Progressive learner path

        1. Read `REQUIREMENTS.md`, `CONCEPTS.md`, and `DESIGN_QUESTIONS.md`.
        2. Implement the contract in `starter/http_service.py`.
        3. Run `public_tests/` against only the starter tree.
        4. Stress parsing, overload, and shutdown behavior before revealing `sealed/`.
        5. Reveal the reference and compare it with two concurrency alternatives that share the
           same import/API contract.
        6. Reproduce the isolated debugging challenge and submit a review for the cache PR.
        7. Run the benchmark on your own machine and interpret raw measurements before reading the
           production gap review.

        `sealed/` is a reveal boundary for human learning, not a claim of hostile multi-user
        sandboxing. Copy `starter/`, `public_tests/`, and the top-level learner documents to create a
        student view; do not mount `sealed/` into that view.

        ## Commands

        ```sh
        # Learner-visible contract (expected to fail until starter is implemented)
        PYTHONPATH=starter python3 -m unittest discover -s public_tests -v

        # Reference and two architecture alternatives
        PYTHONPATH=sealed/reference:sealed/shared python3 -m unittest discover -s public_tests -v
        PYTHONPATH=sealed/alternatives/thread_per_connection:sealed/shared python3 -m unittest discover -s public_tests -v
        PYTHONPATH=sealed/alternatives/event_loop:sealed/shared python3 -m unittest discover -s public_tests -v

        # Run every bounded factory check, including fresh measured benchmark output
        python3 scripts/run_all.py
        ```

        Validation labels are evidence-scoped. Passing these bounded checks supports `BUILDS`,
        `TESTED`, `FUZZED`, `BENCHMARKED`, and `REVIEWED` only alongside `PARTIAL`. It does not support
        `PRODUCTIONIZED`: see `production/PRODUCTIONIZATION.md` for unresolved work.

        ## Navigation

        - `starter/`, `public_tests/`: initial exercise surface
        - `sealed/reference/`, `sealed/reference_tests/`: tested solution and withheld checks
        - `sealed/alternatives/`: bounded worker-pool, thread-per-connection, and selector comparison
        - `adversarial/`: deterministic parser, injected-fault, and slow-client probes
        - `benchmarks/`: actual local execution and raw JSON measurements
        - `debugging/partial-body/`: one-root-cause failure with sealed diagnosis and patch
        - `review_exercises/cache-layer/`: plausible performance PR and expected review
        - `production/`: operations sketch and honest non-production limitations
        """,
    )
    _write_json(
        workspace,
        "MANIFEST.yaml",
        {
            "schema_version": 1,
            "artifact_revision": 1,
            "project_id": "bounded-http-counter-service",
            "title": "Bounded HTTP/1.1 Counter Service",
            "family": "networking-and-production-services",
            "type": "build-your-own-x-challenge-pack",
            "languages": ["Python 3.11"],
            "concepts": [
                "incremental protocol parsing",
                "bounded concurrency",
                "backpressure",
                "idempotency",
                "optimistic concurrency",
                "fault containment",
                "graceful shutdown",
                "observability",
                "benchmark interpretation",
            ],
            "difficulty": 7,
            "estimated_human_hours": 14,
            "production_relevance": 9,
            "cs_depth": 7,
            "debugging_value": 8,
            "architecture_value": 9,
            "status": "GENERATED_CANDIDATE",
            "deployment_status": "NOT_PRODUCTION_READY",
            "productionized": False,
            "reference_architecture": "bounded-worker-pool",
            "alternative_architectures": [
                "bounded-thread-per-connection",
                "single-threaded-selector-loop",
            ],
            "validation_targets": [
                "BUILDS",
                "TESTED",
                "FUZZED",
                "BENCHMARKED",
                "REVIEWED",
                "PARTIAL",
            ],
            "provenance_file": "PROVENANCE.json",
        },
    )
    _write_json(
        workspace,
        "PROVENANCE.json",
        {
            "schema_version": 1,
            "catalog_source": provenance,
            "derivation": {
                "source_derived": [
                    "project category and outbound catalog relationship only",
                    "source repository identity, commit, URL, and license metadata",
                ],
                "agent_generated": [
                    "requirements and learner scaffolding",
                    "all Python implementation and tests",
                    "architecture alternatives",
                    "debugging and review exercises",
                    "production gap analysis",
                ],
                "measured": [
                    "benchmarks/results/smoke.json only after benchmark.py executes",
                    "controller validation logs outside this candidate tree",
                ],
                "inferred": [
                    "difficulty, human-hours estimate, concept tags, and priority scores",
                ],
            },
            "content_boundary": (
                "No linked tutorial content is mirrored; follow the recorded public URL under its "
                "own terms if a learner intentionally retrieves it."
            ),
            "network_used_during_generation": False,
        },
    )
    _write_json(
        workspace,
        "CATALOG_ENTRY.json",
        {
            "schema_version": 1,
            "id": "bounded-http-counter-service",
            "name": "Bounded HTTP/1.1 Counter Service",
            "family": "networking",
            "type": "build",
            "languages": ["python"],
            "concepts": [
                "http-1.1",
                "parsing",
                "concurrency",
                "backpressure",
                "reliability",
                "observability",
            ],
            "difficulty": 7,
            "estimated_human_hours": 14,
            "production_relevance": 9,
            "prerequisites": ["tcp-sockets", "python-threading", "json-apis"],
            "next": ["reverse-proxy", "durable-job-service", "async-runtime"],
            "artifact_paths": {
                "starter": "starter/",
                "reference": "sealed/reference/",
                "alternatives": 2,
                "adversarial": "adversarial/",
                "benchmark": "benchmarks/benchmark.py",
                "debugging_challenges": 1,
                "review_exercises": 1,
            },
            "validation_status": "CANDIDATE_REQUIRES_EXTERNAL_VALIDATION",
            "productionized": False,
            "provenance": "PROVENANCE.json",
        },
    )
    _write(
        workspace,
        "REQUIREMENTS.md",
        """
        # Requirements

        ## Protocol boundary

        Implement an incremental HTTP/1.1 request parser. It must tolerate arbitrary TCP
        fragmentation and multiple requests in one read. Require origin-form targets and exactly one
        nonempty `Host`; reject obsolete folding, duplicate headers, bare-newline framing, unsupported
        versions, and `Transfer-Encoding`. Accept decimal `Content-Length` only. Enforce header and
        body bounds before allocating or waiting for unbounded input. Never interpret a partial body
        as a complete request.

        Responses must include an accurate `Content-Length` and explicit connection policy. Support
        bounded keep-alive and close malformed connections after one structured error. This exercise
        deliberately omits chunked coding, request trailers, upgrades, TLS, proxies, and HTTP/2; do
        not silently pretend those features work.

        ## Application contract

        - `GET /healthz` returns JSON health.
        - `GET /metrics` exposes minimal process-local counters.
        - `PUT /v1/counters/{name}` accepts exactly `{"value": integer}` and returns a version/ETag.
        - `GET /v1/counters/{name}` returns its value and version.
        - `DELETE /v1/counters/{name}` removes it.
        - `POST /v1/counters/{name}/increment` accepts exactly `{"delta": integer}`.
        - A bounded `Idempotency-Key` cache makes repeated increments with the same key and operation
          return the same response without applying twice. Reusing a key for a different counter or
          delta returns deterministic `409 Conflict` rather than another operation's response.
        - `If-Match` on PUT prevents stale writers from overwriting a newer version.

        Names and integers are bounded. Invalid media types, JSON, methods, routes, and versions must
        return stable 4xx results. Internal exception details must not cross the protocol boundary.

        ## Server/lifecycle contract

        Export `ServiceConfig`, `Request`, `Response`, `ProtocolError`, `HTTPParser`, `CounterApp`, and
        `Server` from `http_service`. `Server.start()`, `.address`, `.close()`, and context management
        form the shared architecture contract. Bind only IPv4 loopback in this pack. Capacity,
        queued work, body size, header size, per-connection requests, and read time must be bounded.
        Slow partial requests must eventually release capacity. `close()` must actively unblock idle
        accepted clients and stop within the configured `shutdown_timeout`, even when `read_timeout`
        is longer. The shutdown deadline is a total budget, not a fresh wait for every thread.

        ## Definition of done

        Syntax is not completion. A candidate must pass public and withheld behavioral tests in an
        independent implementation path, survive deterministic parser/fault/slow-client probes, and
        produce benchmark evidence by actual execution. Record limitations. These bounded checks
        remain `PARTIAL`; deployment needs threat modeling, real load tests, persistence decisions,
        TLS/proxy policy, telemetry integration, and operational drills.
        """,
    )
    _write(
        workspace,
        "CONCEPTS.md",
        """
        # Concepts to learn

        ## A byte stream has no messages

        TCP may split one request across reads or combine several requests in one read. Parser state
        therefore owns an input buffer and emits only frames proven complete by syntax and length.
        Limits are part of correctness: a parser that waits forever for an advertised terabyte body
        is operationally incorrect even if its grammar is elegant.

        ## Concurrency is a resource policy

        A worker pool bounds threads and queues work, per-connection threads simplify local control
        flow but require an admission limit, and an event loop makes connection state explicit while
        forbidding blocking handlers. None is universally best. Compare code complexity, tail
        latency, overload response, shutdown, and failure isolation using the same service contract.

        ## Delivery and application semantics differ

        A client can lose a response after a mutation commits and retry. An idempotency key lets the
        application recognize that retry. Its scope, retention, capacity, authentication identity,
        and durable lifetime are product decisions, not an HTTP parser feature.

        ## Observability changes debugging cost

        Health is not readiness, counters are not traces, and a process-local metric is lost on
        restart. Still, explicit fault counters, bounded error responses, environment capture, and
        raw benchmark samples provide much stronger evidence than “it seemed fast.”
        """,
    )
    _write(
        workspace,
        "DESIGN_QUESTIONS.md",
        """
        # Design questions

        1. At what exact point can the parser prove a request body is complete?
        2. Which ambiguous request forms could enable request smuggling when a proxy disagrees?
        3. What is the overload behavior when workers and the queue are both occupied?
        4. Which shutdown invariants protect accepted sockets, queued sockets, and worker threads?
        5. Does an idempotency key belong globally, per route, or per authenticated principal?
        6. How would persistence change acknowledgement and retry semantics?
        7. Which handlers are safe in a single selector thread? How would blocking storage alter that?
        8. Which benchmark result would falsify your architecture hypothesis, and what profile would
           you capture next?
        9. What must be trusted when the service is behind a TLS terminator or reverse proxy?
        10. Which facts make `/healthz` insufficient as a readiness or correctness signal?
        """,
    )
    _write(
        workspace,
        "AGENTS.md",
        """
        # Exercise agent boundary

        Work only in a copied learner view containing top-level requirements, `starter/`, and
        `public_tests/`. Do not mount or search `sealed/`. Use argv-based local commands and IPv4
        loopback only; this exercise needs no external network. Preserve failing commands and concise
        debugging observations. A verbal claim that tests pass is not evidence.
        """,
    )
    _write(workspace, "starter/http_service.py", _STARTER)
    _write(
        workspace,
        "starter/README.md",
        """
        # Starter

        Fill in `http_service.py` without changing its exported contract. Begin with parser unit
        tests, then the application state machine, then one bounded server architecture. Run:

        ```sh
        PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
        ```

        Public tests are necessary but intentionally incomplete. Write tests for fragmented bodies,
        overload, shutdown, concurrent increments, malformed framing, and injected handler failure.
        """,
    )
    _write(workspace, "public_tests/test_http_service.py", _PUBLIC_TESTS)

    _write(workspace, "sealed/shared/http_core.py", _HTTP_CORE)
    _write(workspace, "sealed/reference/http_service.py", _WORKER_POOL)
    _write(workspace, "sealed/reference_tests/test_contract.py", _HIDDEN_TESTS)
    _write(
        workspace,
        "sealed/DESIGN.md",
        """
        # Reference design

        The shared core separates byte-stream parsing, application semantics, response serialization,
        and connection handling. The reference server owns a fixed worker set and bounded queue. The
        acceptor either enqueues a socket or immediately returns 503; each worker owns exactly one
        socket at a time and always completes its queue accounting. A stop event, listener close,
        pending-socket drain, sentinels, and bounded joins make lifecycle ownership explicit.

        The application serializes mutations under one re-entrant lock. This is deliberately simple:
        it prevents lost updates and protects the LRU idempotency map, but constrains throughput. The
        parser rejects transfer coding and duplicate headers rather than implementing ambiguous
        combinations. Tight feature scope is a security and teaching choice, not full HTTP compliance.
        """,
    )
    _write(
        workspace,
        "sealed/TRADEOFFS.md",
        """
        # Architecture tradeoffs

        The worker pool reuses a bounded number of threads and makes blocking handlers tolerable, but
        slow clients occupy workers unless reads time out. Per-connection threads make ownership and
        stack traces direct, but thread creation and memory grow to the admission bound. The selector
        loop keeps one explicit state object per connection and avoids a thread per idle socket, but
        one blocking application call stalls every connection and lifecycle code becomes less linear.

        All three share parser and application semantics so tests and benchmark workloads compare the
        concurrency mechanisms rather than three accidental APIs. One bounded smoke run cannot rank
        them generally; profile under representative handlers, connection reuse, slow clients, and
        saturation before choosing.
        """,
    )
    _write(
        workspace,
        "sealed/REVIEW.md",
        """
        # Senior engineer review

        The reference is a useful tested teaching system, not a server I would expose to untrusted
        traffic. It implements only a narrow HTTP subset; parsing has not been differentially tested
        against a production proxy; errors and metrics lack request correlation; application state and
        idempotency records vanish on restart; key scope is process-global; and overload policy is
        fixed. The GIL and one app lock
        limit CPU scaling. There is no authentication, authorization, TLS, config reload, readiness
        dependency check, deployment packaging, SLO, or compatibility migration policy.

        Good next changes are not “add every production feature.” First define deployment topology and
        durability semantics, then threat-model proxy/parser disagreement, integrate structured logs
        and latency histograms, exercise saturation and shutdown under load, and decide whether to use
        a maintained HTTP stack rather than owning protocol risk.
        """,
    )
    _write(
        workspace,
        "sealed/alternatives/CONTRACT.md",
        """
        # Shared alternative contract

        Every implementation exports the same seven symbols from `http_service` and accepts the same
        `ServiceConfig`. `start()` binds an ephemeral loopback address when port is zero. `address`
        becomes available after start. `close()` performs bounded shutdown. All variants use the same
        parser, response framing, counter application, public tests, withheld tests, adversarial input,
        and benchmark workload. Only connection scheduling/lifecycle architecture differs.
        """,
    )
    _write(
        workspace,
        "sealed/alternatives/thread_per_connection/http_service.py",
        _THREAD_PER_CONNECTION,
    )
    _write(
        workspace,
        "sealed/alternatives/thread_per_connection/README.md",
        """
        # Bounded thread per connection

        Admission uses a semaphore; each admitted socket receives a dedicated short-lived thread.
        Shutdown snapshots sockets/threads under a lock, closes sockets to unblock reads, then joins.
        The model is locally readable and accommodates blocking handlers, but thread churn and stack
        memory scale with the connection cap.
        """,
    )
    _write(workspace, "sealed/alternatives/event_loop/http_service.py", _EVENT_LOOP)
    _write(
        workspace,
        "sealed/alternatives/event_loop/README.md",
        """
        # Single selector event loop

        One thread owns nonblocking sockets and explicit parser/output state. It caps live connection
        objects and expires inactive clients. This reduces idle-thread cost, but `CounterApp.handle`
        runs on the loop: any future blocking database or DNS call would create head-of-line blocking.
        A production design would separate nonblocking I/O ownership from bounded application work.
        """,
    )

    _write(workspace, "adversarial/parser/check.py", _PARSER_ADVERSARY)
    _write(workspace, "adversarial/fault-injection/check.py", _FAULT_CHECK)
    _write(workspace, "adversarial/slow-client/check.py", _SLOW_CLIENT_CHECK)
    _write(
        workspace,
        "adversarial/README.md",
        """
        # Adversarial checks

        The parser campaign uses a fixed seed, randomized fragmentation of valid bytes, and explicit
        ambiguous/invalid forms. Fault injection proves exception details stay private and a later
        health request succeeds. The slow-client check occupies workers with incomplete headers,
        waits for the configured deadline, and verifies capacity recovers. They are deterministic,
        bounded smoke probes—not evidence against all request smuggling, denial-of-service, races, or
        platform-specific socket failures.
        """,
    )

    _write(workspace, "benchmarks/benchmark.py", _BENCHMARK)
    _write(
        workspace,
        "benchmarks/README.md",
        """
        # Benchmark

        `benchmark.py` starts each architecture on IPv4 loopback, verifies a warm-up, then records raw
        nanosecond samples for sequential and four-way burst health requests. It writes machine,
        interpreter, workload, hypothesis, raw samples, summaries, and an interpretation boundary.

        ```sh
        python3 benchmarks/benchmark.py --requests 40 --concurrency 4 \
          --output benchmarks/results/smoke.json
        ```

        The generated pack intentionally contains no result file before execution. Do not compare a
        single smoke ratio as a capacity claim. Repeat runs, add confidence intervals, saturate queues,
        vary keep-alive and handler cost, and profile before drawing an architecture conclusion.
        """,
    )

    buggy_core = _HTTP_CORE.replace(
        """                if len(self._buffer) < header_end + length:
                    return requests
                body = bytes(self._buffer[header_end : header_end + length])
""",
        """                if len(self._buffer) < header_end + length:
                    if len(self._buffer) == header_end:
                        return requests
                    length = len(self._buffer) - header_end
                body = bytes(self._buffer[header_end : header_end + length])
""",
        1,
    )
    if buggy_core == _HTTP_CORE:
        raise RuntimeError("failed to construct the intentional partial-body bug")
    _write(workspace, "debugging/partial-body/buggy/http_core.py", buggy_core)
    _write(workspace, "debugging/partial-body/regression.py", _DEBUG_REGRESSION)
    _write(
        workspace,
        "debugging/partial-body/README.md",
        """
        # Debugging challenge: intermittent JSON rejection

        Under some client/network timings, PUT requests return a JSON error or appear to leave bytes
        for the next request. Sending the same bytes in one local write often succeeds. The failure is
        reproducible without external network access:

        ```sh
        PYTHONPATH=debugging/partial-body/buggy python3 debugging/partial-body/regression.py
        ```

        Investigate byte-stream assumptions, capture the smallest failing split, and add a regression
        before revealing `sealed/`. This challenge has one intentional root cause; do not “fix” it by
        adding sleeps or changing the advertised body length.
        """,
    )
    patch = "".join(
        unified_diff(
            dedent(buggy_core).lstrip("\n").splitlines(keepends=True),
            dedent(_HTTP_CORE).lstrip("\n").splitlines(keepends=True),
            fromfile="a/debugging/partial-body/buggy/http_core.py",
            tofile="b/debugging/partial-body/buggy/http_core.py",
        )
    )
    _write(workspace, "debugging/partial-body/sealed/patch.diff", patch)
    _write(
        workspace,
        "debugging/partial-body/sealed/root-cause.md",
        """
        # Root cause

        The parser treated any body bytes already present after the header as the complete body, even
        when fewer than the declared `Content-Length` had arrived. TCP fragmentation therefore caused
        early request emission; the application saw truncated JSON and the remaining bytes polluted
        subsequent parsing. The single fix is to retain parser state and return no request until the
        entire declared body is buffered.
        """,
    )
    _write(
        workspace,
        "debugging/partial-body/sealed/investigation.md",
        """
        # Investigation

        1. Reproduced with the header plus only five body bytes in the first parser feed.
        2. Verified the advertised length and complete combined payload were correct.
        3. Compared one-write success with split-write failure, isolating stream reassembly rather than
           JSON semantics or application locking.
        4. Asserted that the first feed emits zero requests and the second emits exactly one full body.
        5. Ran the same regression against the corrected shared parser.
        """,
    )

    _write(
        workspace,
        "review_exercises/cache-layer/README.md",
        """
        # PR review: “Cache GET responses to reduce handler latency”

        The proposed patch adds a small wrapper intended to cache successful GET responses. Review it
        as if it were headed toward an authenticated counter/account service. Write `REVIEW.md` with
        location, severity, concrete failure scenario, and suggested direction. Consider correctness,
        security boundaries, concurrency, resource limits, latency, invalidation, observability, and
        lifecycle. Avoid generic style comments unless they obscure a real invariant.

        The patch is syntactically valid and its headline happy path works. A sealed executable
        demonstration and expected review are available after submission.
        """,
    )
    _write(workspace, "review_exercises/cache-layer/proposed/cache_layer.py", _REVIEW_CACHE)
    _write(
        workspace,
        "review_exercises/cache-layer/proposed.patch",
        """
        Subject: [PATCH] Cache GET responses to reduce handler latency

        Add `ResponseCache`, a lock-protected in-memory cache in front of the application. Successful
        GET results are keyed by request target, avoiding duplicate calls for common API reads.

        See `proposed/cache_layer.py` for the reviewable implementation.
        """,
    )
    _write(
        workspace,
        "review_exercises/cache-layer/sealed/EXPECTED_REVIEW.md",
        """
        # Expected review

        ## Critical: cache key crosses authorization principals

        The key is only `request.target`. A response for authenticated Alice at `/v1/me` is returned
        to Bob. Either do not cache personalized data or include a verified authorization/tenant and
        representation context in a carefully specified key. The sealed demonstration reproduces the
        disclosure.

        ## Major: no invalidation or freshness contract

        Successful GETs live forever and mutations do not invalidate them, so clients can observe
        stale state indefinitely. Define cacheable routes, validators/versions, TTL, and mutation
        invalidation based on application semantics.

        ## Major: unbounded memory controlled by request targets

        Every distinct query string/path can add an entry. Add canonicalization, a hard capacity,
        eviction metrics, and admission rules; account for response body size, not only entry count.

        ## Major: application work occurs under the global cache lock

        A slow miss serializes every cached GET and turns one backend stall into head-of-line blocking.
        Use a bounded single-flight design per key or call the backend outside the global metadata lock
        while accepting/documenting duplicate fills.

        ## Minor: no cache outcome observability

        Hit, miss, eviction, fill duration, and size signals are necessary to validate the claimed
        latency improvement and spot churn. This is secondary to the correctness and security issues.
        """,
    )
    _write(
        workspace,
        "review_exercises/cache-layer/sealed/demonstrate.py",
        _REVIEW_DEMONSTRATION,
    )

    _write(
        workspace,
        "production/PRODUCTIONIZATION.md",
        """
        # Productionization gap analysis

        This artifact is **not production-ready** and validators must retain `PARTIAL`. The reference
        demonstrates useful production habits—strict bounds, overload response, explicit lifecycle,
        idempotency semantics, fault containment, health, minimal metrics, adversarial checks, and raw
        benchmark evidence—but important requirements remain deployment-specific and unimplemented.

        Before exposure beyond loopback, choose a maintained HTTP/TLS stack or fund protocol security
        ownership; test parsing agreement with every proxy; define authentication, authorization,
        tenant isolation, request IDs, audit logs, secret handling, and abuse limits. Decide whether
        counter/idempotency state is durable and how retries behave across restart. Add structured
        logging, latency/error/saturation metrics, tracing context, readiness, SLOs, alerts, and
        dashboards. Exercise rolling shutdown, saturation, dependency failure, restore, migration,
        clock issues, and rollback. Package reproducibly and patch dependencies/toolchains.

        The selector alternative also needs a bounded application executor before any handler may
        block. The thread-per-connection version needs memory/stack capacity measurements. The worker
        pool needs representative slow-client and queue-policy testing. None has been fuzzed at scale,
        audited, load-tested on a target host, or operated through an incident.
        """,
    )
    _write(
        workspace,
        "production/OPERATIONS.md",
        """
        # Teaching operations runbook

        ## Signals

        Probe `/healthz` only for process/event-loop reachability. Scrape `/metrics` for request and
        contained-application-error counts, understanding they reset on restart. Capture queue/admission
        metrics as the first extension. Use benchmark JSON only with its environment and parameters.

        ## Slow or unavailable service

        Check worker/connection saturation, partial-request timeouts, handler latency, and error rate.
        Preserve raw requests with secrets removed. Shed load rather than raising limits blindly. A 503
        from admission is intentional overload behavior; a timeout while the queue is unbounded would
        be a design defect.

        ## Shutdown

        Stop admission, close the listener, bound connection drain, unblock readers, and join owners.
        This teaching implementation closes accepted sockets to unblock readers, then joins all owners
        against one configured `shutdown_timeout`; it does not guarantee completion of in-flight work.
        A real service must publish its termination grace period and retry safety.
        """,
    )
    _write(
        workspace,
        "environment/README.md",
        """
        # Reproducible environment

        Required: CPython 3.11 or newer on a platform with IPv4 loopback and the standard-library
        `selectors`, `socket`, and `threading` modules. No packages and no external network are used.
        Commands are argv-based; validation sets bytecode suppression and a deterministic C.UTF-8
        locale. Exact OS/interpreter information is captured by the benchmark at execution time.
        """,
    )
    _write(workspace, "environment/requirements.txt", "# Python 3.11 standard library only\n")
    _write(workspace, "environment/check_python.py", _SYNTAX_CHECKER)
    _write(workspace, "scripts/run_all.py", _RUN_ALL)

    validators: list[dict[str, Any]] = [
        {
            "type": "required_paths",
            "name": "http-pack-layout",
            "paths": [
                "README.md",
                "MANIFEST.yaml",
                "PROVENANCE.json",
                "CATALOG_ENTRY.json",
                "REQUIREMENTS.md",
                "CONCEPTS.md",
                "DESIGN_QUESTIONS.md",
                "starter/http_service.py",
                "public_tests/test_http_service.py",
                "sealed/shared/http_core.py",
                "sealed/reference/http_service.py",
                "sealed/reference_tests/test_contract.py",
                "sealed/alternatives/thread_per_connection/http_service.py",
                "sealed/alternatives/event_loop/http_service.py",
                "adversarial/parser/check.py",
                "adversarial/fault-injection/check.py",
                "adversarial/slow-client/check.py",
                "benchmarks/benchmark.py",
                "debugging/partial-body/buggy/http_core.py",
                "debugging/partial-body/regression.py",
                "debugging/partial-body/sealed/patch.diff",
                "review_exercises/cache-layer/proposed/cache_layer.py",
                "review_exercises/cache-layer/sealed/EXPECTED_REVIEW.md",
                "production/PRODUCTIONIZATION.md",
                "scripts/run_all.py",
            ],
        },
        {
            "type": "forbidden_paths",
            "name": "starter-reveal-boundary",
            "paths": [
                "starter/sealed",
                "starter/reference",
                "starter/hidden_tests",
                "starter/EXPECTED_REVIEW.md",
                "public_tests/sealed",
            ],
        },
        {
            "type": "json_fields",
            "name": "provenance-fields",
            "path": "PROVENANCE.json",
            "required": [
                "schema_version",
                "catalog_source",
                "derivation",
                "content_boundary",
                "network_used_during_generation",
            ],
        },
        {
            "type": "json_fields",
            "name": "catalog-fields",
            "path": "CATALOG_ENTRY.json",
            "required": [
                "schema_version",
                "id",
                "family",
                "languages",
                "concepts",
                "difficulty",
                "artifact_paths",
                "validation_status",
                "provenance",
            ],
        },
        {
            "type": "command",
            "name": "http-python-syntax",
            "argv": ["python3", "environment/check_python.py"],
            "timeout_seconds": 30,
            "claims": ["BUILDS", "PARTIAL"],
        },
    ]
    implementation_paths = {
        "reference": "sealed/reference:sealed/shared",
        "thread-per-connection": "sealed/alternatives/thread_per_connection:sealed/shared",
        "event-loop": "sealed/alternatives/event_loop:sealed/shared",
    }
    for name, python_path in implementation_paths.items():
        validators.extend(
            [
                {
                    "type": "command",
                    "name": f"{name}-public-contract",
                    "argv": [
                        "python3",
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "public_tests",
                        "-v",
                    ],
                    "env": {"PYTHONPATH": python_path},
                    "timeout_seconds": 45,
                    "claims": ["TESTED", "PARTIAL"],
                },
                {
                    "type": "command",
                    "name": f"{name}-withheld-contract",
                    "argv": [
                        "python3",
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "sealed/reference_tests",
                        "-v",
                    ],
                    "env": {"PYTHONPATH": python_path},
                    "timeout_seconds": 60,
                    "claims": ["TESTED", "PARTIAL"],
                },
            ]
        )
    validators.extend(
        [
            {
                "type": "command",
                "name": "deterministic-parser-adversary",
                "argv": [
                    "python3",
                    "adversarial/parser/check.py",
                    "--seed",
                    "20260830",
                    "--iterations",
                    "120",
                ],
                "env": {"PYTHONPATH": implementation_paths["reference"]},
                "timeout_seconds": 30,
                "claims": ["FUZZED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "fault-containment-check",
                "argv": ["python3", "adversarial/fault-injection/check.py"],
                "env": {"PYTHONPATH": implementation_paths["reference"]},
                "timeout_seconds": 30,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "slow-client-capacity-recovery",
                "argv": ["python3", "adversarial/slow-client/check.py"],
                "env": {"PYTHONPATH": implementation_paths["reference"]},
                "timeout_seconds": 30,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "debugging-bug-reproduces",
                "argv": ["python3", "debugging/partial-body/regression.py"],
                "env": {"PYTHONPATH": "debugging/partial-body/buggy"},
                "expected_exit": 1,
                "timeout_seconds": 20,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "debugging-reference-regression",
                "argv": ["python3", "debugging/partial-body/regression.py"],
                "env": {"PYTHONPATH": "sealed/shared"},
                "timeout_seconds": 20,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "review-security-finding-demonstration",
                "argv": [
                    "python3",
                    "review_exercises/cache-layer/sealed/demonstrate.py",
                ],
                "env": {
                    "PYTHONPATH": "review_exercises/cache-layer/proposed:sealed/shared"
                },
                "timeout_seconds": 20,
                "claims": ["TESTED", "REVIEWED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "measured-architecture-benchmark",
                "argv": [
                    "python3",
                    "benchmarks/benchmark.py",
                    "--requests",
                    "40",
                    "--concurrency",
                    "4",
                    "--output",
                    "benchmarks/results/smoke.json",
                ],
                "produces": ["benchmarks/results/smoke.json"],
                "timeout_seconds": 60,
                "claims": ["BENCHMARKED", "PARTIAL"],
            },
            {
                "type": "json_fields",
                "name": "benchmark-evidence-fields",
                "path": "benchmarks/results/smoke.json",
                "required": [
                    "schema_version",
                    "hypothesis",
                    "parameters",
                    "environment",
                    "raw_results",
                    "interpretation_boundary",
                ],
            },
            {"type": "tree_checksum", "name": "http-pack-tree-checksum"},
        ]
    )

    generated_files = sorted(path for path in workspace.rglob("*") if path.is_file())
    metadata = {
        "name": "Bounded HTTP/1.1 Counter Service",
        "family": "networking-and-production-services",
        "type": "build-your-own-x-challenge-pack",
        "languages": ["Python 3.11"],
        "concepts": [
            "HTTP parsing",
            "bounded concurrency",
            "backpressure",
            "idempotency",
            "fault containment",
            "observability",
        ],
        "difficulty": 7,
        "estimated_human_hours": 14,
        "production_relevance": 9,
        "provenance": provenance,
        "validation_targets": [
            "BUILDS",
            "TESTED",
            "FUZZED",
            "BENCHMARKED",
            "REVIEWED",
            "PARTIAL",
        ],
        "deployment_status": "NOT_PRODUCTION_READY",
        "productionized": False,
        "architecture_count": 3,
    }
    evidence = {
        "handler": "generate_http_service_slice",
        "project_id": "bounded-http-counter-service",
        "external_validation_required": True,
        "validator_count": len(validators),
        "generated_file_count": len(generated_files),
        "generated_bytes": sum(path.stat().st_size for path in generated_files),
        "candidate_tree_sha256": tree_sha256(workspace),
        "benchmark_generated_during_validation": True,
        "deployment_status": "NOT_PRODUCTION_READY",
    }
    return SliceResult(
        evidence,
        validators,
        "http_service_challenge_pack",
        "projects/networking/bounded-http-counter-service",
        metadata,
    )
