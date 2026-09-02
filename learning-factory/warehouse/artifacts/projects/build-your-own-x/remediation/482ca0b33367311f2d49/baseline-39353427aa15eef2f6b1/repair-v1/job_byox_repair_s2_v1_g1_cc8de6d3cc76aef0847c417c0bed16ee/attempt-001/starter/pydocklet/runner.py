"""Bounded argv-only subprocess execution (milestone 5)."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from .models import ExecutionResult


class ProcessRunner:
    def __init__(
        self, max_output_bytes: int = 64 * 1024, scratch_dir: Path | None = None
    ) -> None:
        if (
            not isinstance(max_output_bytes, int)
            or isinstance(max_output_bytes, bool)
            or max_output_bytes < 0
        ):
            raise ValueError("max_output_bytes must be a non-negative integer")
        self.max_output_bytes = max_output_bytes
        self.scratch_dir = None if scratch_dir is None else Path(scratch_dir)

    def run(
        self,
        argv: Sequence[str],
        cwd: Path,
        env: Mapping[str, str] | None = None,
        timeout: float = 5.0,
    ) -> ExecutionResult:
        """TODO(5): execute without a shell; keep each serialized log within its byte limit."""
        raise NotImplementedError("TODO(5): ProcessRunner.run")
