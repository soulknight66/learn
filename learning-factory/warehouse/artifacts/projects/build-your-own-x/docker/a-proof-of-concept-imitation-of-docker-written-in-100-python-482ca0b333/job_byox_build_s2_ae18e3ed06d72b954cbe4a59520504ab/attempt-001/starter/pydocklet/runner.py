"""Bounded argv-only subprocess execution (milestone 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from .models import ExecutionResult


class ProcessRunner:
    def __init__(self, max_output_bytes: int = 64 * 1024) -> None:
        if max_output_bytes < 0:
            raise ValueError("max_output_bytes must be non-negative")
        self.max_output_bytes = max_output_bytes

    def run(
        self,
        argv: Sequence[str],
        cwd: Path,
        env: Mapping[str, str] | None = None,
        timeout: float = 5.0,
    ) -> ExecutionResult:
        """TODO(5): validate and execute without a shell; bound both logs independently."""
        raise NotImplementedError("TODO(5): ProcessRunner.run")
