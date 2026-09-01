"""Linux namespace planning and bounded process execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .models import ContainerSpec
from .state import StateStore


class RuntimeBackend(Protocol):
    def build_argv(self, rootfs: Path, spec: ContainerSpec) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class RunResult:
    container_id: str
    argv: tuple[str, ...]
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool
    output_truncated: bool


class LinuxNamespaceBackend:
    def __init__(self, executable: str = "unshare") -> None:
        self.executable = executable

    def build_argv(self, rootfs: Path, spec: ContainerSpec) -> tuple[str, ...]:
        raise NotImplementedError("milestone 4: construct an argv-only namespace plan")


class Runner:
    def __init__(
        self,
        state: StateStore,
        rootfs_for: Callable[[str], Path],
        *,
        backend: RuntimeBackend | None = None,
        timeout: float = 10.0,
        max_output: int = 1024 * 1024,
    ) -> None:
        raise NotImplementedError("milestone 4: validate bounded runner settings")

    def run(self, container_id: str) -> RunResult:
        raise NotImplementedError("milestone 4: launch, drain, time out, and record state")
