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
