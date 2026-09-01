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
