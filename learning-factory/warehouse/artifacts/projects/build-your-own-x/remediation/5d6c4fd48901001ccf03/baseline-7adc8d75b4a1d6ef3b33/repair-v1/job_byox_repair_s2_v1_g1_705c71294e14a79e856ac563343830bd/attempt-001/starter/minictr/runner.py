"""Bounded subprocess supervision skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .planner import LaunchPlan


@dataclass(frozen=True, slots=True)
class RunResult:
    exit_code: int
    stdout: bytes
    stderr: bytes
    timed_out: bool


class Runner:
    def __init__(self, popen_factory: Callable[..., Any] | None = None):
        self._popen_factory = popen_factory

    def run(self, plan: LaunchPlan, payload: bytes) -> RunResult:
        # TODO(stage 5): enforce size, launch without a shell, communicate with a timeout, and kill
        # the process group on expiry. The injected factory keeps unit tests unprivileged.
        raise NotImplementedError("stage 5: process supervision")
