"""Stage 4: durable, guarded container lifecycle state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


CREATED = "CREATED"
RUNNING = "RUNNING"
EXITED = "EXITED"
FAILED = "FAILED"


@dataclass(frozen=True)
class ContainerState:
    container_id: str
    status: str
    revision: int
    created_at: float
    updated_at: float
    exit_code: int | None = None
    error: str | None = None


class StateStore:
    """Persist one strict JSON record per container id."""

    def __init__(
        self,
        directory: str | Path,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.directory = Path(directory)
        self.clock = clock

    def create(self, container_id: str) -> ContainerState:
        raise NotImplementedError("stage 4: implement create")

    def get(self, container_id: str) -> ContainerState:
        raise NotImplementedError("stage 4: implement get")

    def transition(
        self,
        container_id: str,
        expected: str,
        target: str,
        *,
        exit_code: int | None = None,
        error: str | None = None,
    ) -> ContainerState:
        raise NotImplementedError("stage 4: implement transition")
