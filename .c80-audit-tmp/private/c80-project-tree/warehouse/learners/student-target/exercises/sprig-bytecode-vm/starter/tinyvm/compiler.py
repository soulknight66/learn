from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instruction:
    opcode: str
    operand: int | str | None = None


@dataclass(frozen=True)
class BytecodeProgram:
    instructions: tuple[Instruction, ...]


def compile_program(program) -> BytecodeProgram:
    # TODO(stage 2): emit stack-balanced instructions and patch structured control flow.
    raise NotImplementedError("implement compile_program")
