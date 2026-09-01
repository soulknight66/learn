from __future__ import annotations

from .compiler import BytecodeProgram, Instruction
from .model import ExecutionResult, ResourceLimit, RuntimeFault
from .semantics import binary, checked, truth


BINARY_OPS = {
    "ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "MOD": "%",
    "EQ": "==", "NE": "!=", "LT": "<", "LE": "<=", "GT": ">", "GE": ">=",
}
NO_OPERAND = {"TICK", "PRINT", "NEG", "NOT", "BOOL", *BINARY_OPS, "HALT"}
NAME_OPERAND = {"LOAD", "DEFINE", "STORE"}
JUMP_OPS = {"JUMP", "JUMP_IF_FALSE", "JUMP_IF_TRUE"}
MAX_INSTRUCTIONS = 100_000


def _valid_name(value: object) -> bool:
    if type(value) is not str or not value:
        return False
    first, rest = value[0], value[1:]
    letter = lambda character: "a" <= character <= "z" or "A" <= character <= "Z"
    digit = lambda character: "0" <= character <= "9"
    return (letter(first) or first == "_") and all(
        letter(character) or digit(character) or character == "_" for character in rest
    )


def verify(program: BytecodeProgram) -> None:
    """Validate an untrusted bytecode graph before executing any instruction."""

    if type(program) is not BytecodeProgram or type(program.instructions) is not tuple:
        raise RuntimeFault("malformed bytecode program")
    instructions = program.instructions
    if not instructions:
        raise RuntimeFault("bytecode program must contain HALT")
    if len(instructions) > MAX_INSTRUCTIONS:
        raise ResourceLimit(f"bytecode exceeds {MAX_INSTRUCTIONS} instructions")
    known = {"CONST", *NAME_OPERAND, *NO_OPERAND, *JUMP_OPS}
    for index, instruction in enumerate(instructions):
        if type(instruction) is not Instruction or type(instruction.opcode) is not str:
            raise RuntimeFault(f"malformed instruction at {index}")
        opcode, operand = instruction.opcode, instruction.operand
        if opcode not in known:
            raise RuntimeFault(f"unknown opcode at {index}: {opcode}")
        if opcode == "CONST" and type(operand) is not int:
            raise RuntimeFault(f"CONST requires an integer operand at {index}")
        if opcode in NAME_OPERAND and not _valid_name(operand):
            raise RuntimeFault(f"{opcode} requires an ASCII identifier at {index}")
        if opcode in NO_OPERAND and operand is not None:
            raise RuntimeFault(f"{opcode} does not accept an operand at {index}")
        if opcode in JUMP_OPS and (
            type(operand) is not int or not 0 <= operand < len(instructions)
        ):
            raise RuntimeFault(f"invalid jump target at {index}: {operand}")
    if instructions[-1].opcode != "HALT":
        raise RuntimeFault("bytecode program must end with HALT")

    incoming_depth = {0: 0}
    pending = [0]
    while pending:
        index = pending.pop()
        depth = incoming_depth[index]
        instruction = instructions[index]
        opcode = instruction.opcode
        required, change = 0, 0
        if opcode in {"CONST", "LOAD"}: change = 1
        elif opcode in {"DEFINE", "STORE", "PRINT"}: required, change = 1, -1
        elif opcode in {"NEG", "NOT", "BOOL"}: required = 1
        elif opcode in BINARY_OPS: required, change = 2, -1
        elif opcode in {"JUMP_IF_FALSE", "JUMP_IF_TRUE"}: required, change = 1, -1
        if depth < required:
            raise RuntimeFault(f"bytecode stack underflow at {index}")
        next_depth = depth + change
        if opcode == "HALT":
            if depth:
                raise RuntimeFault(f"non-empty stack at HALT ({depth} values)")
            successors: tuple[int, ...] = ()
        elif opcode == "JUMP":
            successors = (instruction.operand,)  # type: ignore[assignment]
        elif opcode in {"JUMP_IF_FALSE", "JUMP_IF_TRUE"}:
            successors = (index + 1, instruction.operand)  # type: ignore[assignment]
        else:
            successors = (index + 1,)
        for successor in successors:
            if not 0 <= successor < len(instructions):
                raise RuntimeFault(f"program counter can escape after {index}")
            previous = incoming_depth.get(successor)
            if previous is not None and previous != next_depth:
                raise RuntimeFault(
                    f"inconsistent stack height at {successor}: {previous} versus {next_depth}"
                )
            if previous is None:
                incoming_depth[successor] = next_depth
                pending.append(successor)
    if len(incoming_depth) != len(instructions):
        unreachable = next(index for index in range(len(instructions)) if index not in incoming_depth)
        raise RuntimeFault(f"unreachable bytecode instruction at {unreachable}")


def execute(program: BytecodeProgram, *, max_steps: int = 10_000) -> ExecutionResult:
    if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps <= 0:
        raise ValueError("max_steps must be a positive integer")
    verify(program)
    stack: list[int] = []
    environment: dict[str, int] = {}
    outputs: list[int] = []
    pc = 0
    steps = 0
    dispatches = 0
    dispatch_limit = len(program.instructions) + max_steps * 16 + 16

    def pop() -> int:
        if not stack:
            raise RuntimeFault("bytecode stack underflow")
        return stack.pop()

    while 0 <= pc < len(program.instructions):
        if dispatches >= dispatch_limit:
            raise ResourceLimit("bytecode dispatch safety budget exceeded")
        instruction = program.instructions[pc]
        dispatches += 1
        pc += 1
        opcode, operand = instruction.opcode, instruction.operand
        if opcode == "TICK":
            if steps >= max_steps:
                raise ResourceLimit(f"evaluation budget exceeded ({max_steps})")
            steps += 1
        elif opcode == "CONST":
            stack.append(checked(operand))
        elif opcode == "LOAD":
            if operand not in environment:
                raise RuntimeFault(f"undefined variable: {operand}")
            stack.append(environment[operand])
        elif opcode == "DEFINE":
            if operand in environment: raise RuntimeFault(f"duplicate variable: {operand}")
            environment[operand] = pop()
        elif opcode == "STORE":
            if operand not in environment:
                raise RuntimeFault(f"undefined variable: {operand}")
            environment[operand] = pop()
        elif opcode == "PRINT":
            outputs.append(pop())
        elif opcode == "NEG":
            stack.append(checked(-pop()))
        elif opcode == "NOT":
            stack.append(int(pop() == 0))
        elif opcode == "BOOL":
            stack.append(truth(pop()))
        elif opcode in BINARY_OPS:
            right, left = pop(), pop()
            stack.append(binary(BINARY_OPS[opcode], left, right))
        elif opcode in {"JUMP", "JUMP_IF_FALSE", "JUMP_IF_TRUE"}:
            take = opcode == "JUMP"
            if opcode == "JUMP_IF_FALSE": take = pop() == 0
            if opcode == "JUMP_IF_TRUE": take = pop() != 0
            if take: pc = operand
        elif opcode == "HALT":
            if stack: raise RuntimeFault("non-empty stack at HALT")
            return ExecutionResult(tuple(outputs), dict(environment), steps, "bytecode")
        else:
            raise RuntimeFault(f"unknown opcode: {opcode}")
    raise RuntimeFault("program counter escaped without HALT")
