"""Stable value objects used by the public API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ContainerState(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    EXITED = "EXITED"


@dataclass(frozen=True)
class ImageRecord:
    name: str
    digest: str
    rootfs: Path
    layer_digests: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContainerRecord:
    container_id: str
    image_digest: str
    state: ContainerState
    command: tuple[str, ...]
    env: dict[str, str]
    rootfs: Path
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
