from __future__ import annotations

from .compiler import BytecodeProgram
from .model import ExecutionResult


def execute(program: BytecodeProgram, *, max_steps: int) -> ExecutionResult:
    # TODO(stage 3): validate operands, enforce max_steps, and execute without host eval/exec.
    raise NotImplementedError("implement execute")
