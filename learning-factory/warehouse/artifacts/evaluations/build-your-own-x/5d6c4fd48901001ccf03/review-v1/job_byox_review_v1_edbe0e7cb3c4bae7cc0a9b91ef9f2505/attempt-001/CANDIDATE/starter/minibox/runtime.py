"""Stage 5: coordinate state with an injectable execution backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .config import ContainerSpec
from .state import StateStore


@dataclass(frozen=True)
class ExecutionResult:
    exit_code: int
    stdout: bytes
    stderr: bytes


class ExecutionBackend(Protocol):
    def run(self, spec: ContainerSpec) -> ExecutionResult: ...


class Runtime:
    def __init__(self, store: StateStore, backend: ExecutionBackend) -> None:
        self.store = store
        self.backend = backend

    def run(self, spec: ContainerSpec, container_id: str) -> ExecutionResult:
        """Run once while preserving every observable lifecycle transition."""

        raise NotImplementedError("stage 5: implement Runtime.run")


class LinuxSubprocessBackend:
    """Optional real Linux backend implemented in the final stage."""

    def __init__(
        self,
        *,
        unshare_path: str | None = None,
        python_path: str | None = None,
        max_output_bytes: int = 1_048_576,
    ) -> None:
        raise NotImplementedError("stage 6: implement LinuxSubprocessBackend")

    def run(self, spec: ContainerSpec) -> ExecutionResult:
        raise NotImplementedError("stage 6: implement LinuxSubprocessBackend.run")
