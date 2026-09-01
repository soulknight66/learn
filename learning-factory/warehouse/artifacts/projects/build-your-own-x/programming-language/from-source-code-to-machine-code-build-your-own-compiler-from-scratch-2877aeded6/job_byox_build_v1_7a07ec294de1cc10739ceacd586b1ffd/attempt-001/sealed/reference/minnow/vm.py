"""Execution engine for structurally verified MNO1 bytecode."""

from .bytecode import Opcode, validate
from .errors import RuntimeFault, StepLimitExceeded


MIN_I64 = -(1 << 63)
MAX_I64 = (1 << 63) - 1


def _checked(value):
    if value < MIN_I64 or value > MAX_I64:
        raise RuntimeFault("signed 64-bit arithmetic overflow", code="RUNTIME002")
    return value


def _quotient(left, right):
    if right == 0:
        raise RuntimeFault("division by zero", code="RUNTIME001")
    if left == MIN_I64 and right == -1:
        raise RuntimeFault("signed 64-bit arithmetic overflow", code="RUNTIME002")
    magnitude = abs(left) // abs(right)
    return -magnitude if (left < 0) != (right < 0) else magnitude


def run_bytecode(program, stdout, *, step_limit=1_000_000):
    if not isinstance(program, (bytes, bytearray)):
        raise TypeError("program must be bytes or bytearray")
    if isinstance(step_limit, bool) or not isinstance(step_limit, int):
        raise TypeError("step_limit must be an integer")
    if step_limit <= 0:
        raise ValueError("step_limit must be positive")

    verified = validate(bytes(program))
    locals_ = [0] * verified.slot_count
    stack = []
    address = 0
    steps = 0

    while True:
        if steps >= step_limit:
            raise StepLimitExceeded()
        instruction = verified.by_address[address]
        steps += 1
        next_address = address + instruction.size
        opcode = instruction.opcode

        if opcode is Opcode.CONST:
            stack.append(instruction.operand)
        elif opcode is Opcode.LOAD:
            stack.append(locals_[instruction.operand])
        elif opcode is Opcode.STORE:
            locals_[instruction.operand] = stack.pop()
        elif opcode is Opcode.NEG:
            stack[-1] = _checked(-stack[-1])
        elif opcode is Opcode.NOT:
            stack[-1] = int(stack[-1] == 0)
        elif opcode in (
            Opcode.ADD,
            Opcode.SUB,
            Opcode.MUL,
            Opcode.DIV,
            Opcode.MOD,
            Opcode.EQ,
            Opcode.NE,
            Opcode.LT,
            Opcode.LE,
            Opcode.GT,
            Opcode.GE,
        ):
            right = stack.pop()
            left = stack.pop()
            if opcode is Opcode.ADD:
                result = _checked(left + right)
            elif opcode is Opcode.SUB:
                result = _checked(left - right)
            elif opcode is Opcode.MUL:
                result = _checked(left * right)
            elif opcode is Opcode.DIV:
                result = _quotient(left, right)
            elif opcode is Opcode.MOD:
                quotient = _quotient(left, right)
                result = left - quotient * right
            elif opcode is Opcode.EQ:
                result = int(left == right)
            elif opcode is Opcode.NE:
                result = int(left != right)
            elif opcode is Opcode.LT:
                result = int(left < right)
            elif opcode is Opcode.LE:
                result = int(left <= right)
            elif opcode is Opcode.GT:
                result = int(left > right)
            else:
                result = int(left >= right)
            stack.append(result)
        elif opcode is Opcode.PRINT:
            stdout.write(f"{stack.pop()}\n")
        elif opcode is Opcode.JUMP:
            address = instruction.operand
            continue
        elif opcode is Opcode.JUMP_IF_FALSE:
            condition = stack.pop()
            if condition == 0:
                address = instruction.operand
                continue
        elif opcode is Opcode.HALT:
            return None
        else:  # The validator makes this unreachable.
            raise RuntimeFault("validated program contained an unknown instruction")
        address = next_address
