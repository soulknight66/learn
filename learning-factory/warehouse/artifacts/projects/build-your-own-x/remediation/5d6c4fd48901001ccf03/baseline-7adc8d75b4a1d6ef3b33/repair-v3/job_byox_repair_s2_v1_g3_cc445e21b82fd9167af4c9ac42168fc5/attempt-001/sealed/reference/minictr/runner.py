"""Bounded, injectable subprocess supervision."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import signal
import subprocess
from typing import Any, Callable

from .errors import ValidationError
from .planner import LaunchPlan

MAX_PAYLOAD = 1024 * 1024


@dataclass(frozen=True, slots=True)
class RunResult:
    exit_code: int
    stdout: bytes
    stderr: bytes
    timed_out: bool


class Runner:
    def __init__(
        self,
        popen_factory: Callable[..., Any] | None = None,
        killpg: Callable[[int, int], None] | None = None,
    ):
        self._popen_factory = popen_factory or subprocess.Popen
        self._killpg = killpg or os.killpg

    @staticmethod
    def _canonical_payload(payload: bytes) -> bytes:
        if not isinstance(payload, bytes):
            raise ValidationError("payload must be bytes")
        if len(payload) > MAX_PAYLOAD:
            raise ValidationError("payload exceeds 1 MiB")
        try:
            value = json.loads(payload.decode("utf-8"))
        except (MemoryError, UnicodeDecodeError, RecursionError, ValueError) as exc:
            raise ValidationError("payload must be UTF-8 JSON") from exc
        try:
            canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        except (MemoryError, OverflowError, RecursionError, TypeError, ValueError) as exc:
            raise ValidationError("payload cannot be represented as canonical JSON") from exc
        if len(canonical) > MAX_PAYLOAD:
            raise ValidationError("canonical payload exceeds 1 MiB")
        return canonical

    def run(self, plan: LaunchPlan, payload: bytes) -> RunResult:
        if not isinstance(plan, LaunchPlan):
            raise ValidationError("plan must be a LaunchPlan")
        wire_payload = self._canonical_payload(payload)
        process = self._popen_factory(
            list(plan.argv),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(plan.helper_env_items),
            shell=False,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(input=wire_payload, timeout=plan.timeout_seconds)
            return RunResult(int(process.returncode), stdout, stderr, False)
        except subprocess.TimeoutExpired:
            try:
                self._killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
            returncode = process.returncode
            if returncode is None:
                returncode = -signal.SIGKILL
            return RunResult(int(returncode), stdout, stderr, True)
