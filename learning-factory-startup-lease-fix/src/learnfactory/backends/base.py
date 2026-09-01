from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..sandbox_policy import SandboxRuleManifest


@dataclass(frozen=True)
class BackendResult:
    exit_code: int
    final_message: str
    session_id: str | None = None
    usage: dict[str, object] = field(default_factory=dict)
    timed_out: bool = False
    cancelled: bool = False
    stderr_tail: str = ""


class CodexBackend(Protocol):
    name: str

    def start_job(
        self,
        prompt: str,
        workspace: Path,
        log_dir: Path,
        *,
        output_schema: Path | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
        timeout_seconds: float | None = None,
        cancel_event: threading.Event | None = None,
        sandbox_manifest: SandboxRuleManifest | None = None,
    ) -> BackendResult: ...

    def resume_job(self, session_id: str, prompt: str, workspace: Path, log_dir: Path, **kwargs: object) -> BackendResult: ...

    def interrupt_job(self) -> None: ...

    def get_status(self) -> str: ...

    def terminate_job(self) -> None: ...
