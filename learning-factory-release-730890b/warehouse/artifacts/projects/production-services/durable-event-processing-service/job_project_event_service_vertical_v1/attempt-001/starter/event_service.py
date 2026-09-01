"""Learner starter for a durable event-processing service.

Implement this API using only Python 3.11 and SQLite. Read REQUIREMENTS.md before
changing signatures. The sealed implementation is deliberately not imported here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import time


class LeaseLost(RuntimeError):
    pass


class InjectedCrash(RuntimeError):
    pass


@dataclass(frozen=True)
class Delivery:
    message_id: int
    idempotency_key: str
    payload: dict[str, Any]
    attempt: int
    lease_owner: str
    lease_token: str
    lease_expires_at: float


class EventService:
    def __init__(
        self,
        path: str | Path,
        *,
        clock: Callable[[], float] = time.time,
        max_attempts: int = 3,
        base_backoff: float = 1.0,
        max_payload_bytes: int = 65_536,
    ) -> None:
        raise NotImplementedError("design the schema and migration runner first")

    def ingest(self, idempotency_key: str, payload: dict[str, Any]) -> tuple[int, bool]:
        raise NotImplementedError

    def claim(self, owner: str, *, lease_seconds: float = 30.0) -> Delivery | None:
        raise NotImplementedError

    def heartbeat(self, delivery: Delivery, *, lease_seconds: float = 30.0) -> Delivery:
        raise NotImplementedError

    def deliver(
        self,
        delivery: Delivery,
        result: dict[str, Any] | None = None,
        *,
        fault: str | None = None,
    ) -> bool:
        raise NotImplementedError

    def fail(self, delivery: Delivery, error: str) -> str:
        raise NotImplementedError

    def counts(self) -> dict[str, int]:
        raise NotImplementedError
