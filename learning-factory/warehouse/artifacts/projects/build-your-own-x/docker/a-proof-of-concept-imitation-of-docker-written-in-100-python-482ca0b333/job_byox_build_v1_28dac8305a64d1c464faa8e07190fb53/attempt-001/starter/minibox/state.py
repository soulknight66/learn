"""SQLite-backed container lifecycle state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .models import ContainerSpec, ContainerState


@dataclass(frozen=True)
class ContainerRecord:
    container_id: str
    spec: ContainerSpec
    state: ContainerState
    exit_code: int | None
    created_ns: int
    updated_ns: int


@dataclass(frozen=True)
class StateEvent:
    sequence: int
    container_id: str
    from_state: ContainerState | None
    to_state: ContainerState
    exit_code: int | None
    at_ns: int


class StateStore:
    def __init__(
        self,
        database: str | Path,
        *,
        migrations: str | Path | None = None,
        clock_ns: Callable[[], int] | None = None,
    ) -> None:
        raise NotImplementedError("milestone 3: open the database and apply migrations")

    def create(self, spec: ContainerSpec) -> ContainerRecord:
        raise NotImplementedError("milestone 3: atomically create state and first event")

    def get(self, container_id: str) -> ContainerRecord:
        raise NotImplementedError("milestone 3: retrieve durable state")

    def transition(
        self,
        container_id: str,
        expected: ContainerState,
        target: ContainerState,
        *,
        exit_code: int | None = None,
    ) -> ContainerRecord:
        raise NotImplementedError("milestone 3: compare and transition atomically")

    def events(self, container_id: str) -> list[StateEvent]:
        raise NotImplementedError("milestone 3: retrieve append-only history")
