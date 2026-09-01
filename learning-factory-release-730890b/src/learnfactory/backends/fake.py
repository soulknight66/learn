from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from .base import BackendResult


class FakeBackend:
    name = "fake"

    def __init__(self, *, delay: float = 0, exit_code: int = 0, files: dict[str, str] | None = None):
        self.delay = delay
        self.exit_code = exit_code
        self.files = files or {}
        self._status = "IDLE"

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
    ) -> BackendResult:
        self._status = "RUNNING"
        deadline = time.monotonic() + self.delay
        while time.monotonic() < deadline:
            if cancel_event and cancel_event.wait(0.01):
                self._status = "CANCELLED"
                return BackendResult(130, "cancelled", cancelled=True)
        for relative, content in self.files.items():
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "codex.jsonl").write_text(
            json.dumps({"type": "thread.started", "thread_id": "fake-session"}) + "\n",
            encoding="utf-8",
        )
        self._status = "COMPLETED"
        return BackendResult(self.exit_code, "fake completed", session_id="fake-session")

    def resume_job(self, session_id: str, prompt: str, workspace: Path, log_dir: Path, **kwargs: object) -> BackendResult:
        return self.start_job(prompt, workspace, log_dir, **kwargs)

    def interrupt_job(self) -> None:
        self._status = "INTERRUPTED"

    def get_status(self) -> str:
        return self._status

    def terminate_job(self) -> None:
        self._status = "TERMINATED"
