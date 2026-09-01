"""MNO1 constants, serialization, and structural validation."""

from dataclasses import dataclass
from enum import IntEnum


MAGIC = b"MNO1"
HEADER_SIZE = 10


class Opcode(IntEnum):
    CONST = 0x01
    LOAD = 0x02
    STORE = 0x03
    ADD = 0x10
    SUB = 0x11
    MUL = 0x12
    DIV = 0x13
    MOD = 0x14
    NEG = 0x15
    NOT = 0x16
    EQ = 0x20
    NE = 0x21
    LT = 0x22
    LE = 0x23
    GT = 0x24
    GE = 0x25
    PRINT = 0x30
    JUMP = 0x40
    JUMP_IF_FALSE = 0x41
    HALT = 0xFF


@dataclass(frozen=True, slots=True)
class Instruction:
    address: int
    opcode: Opcode
    operand: int | None
    size: int


@dataclass(frozen=True, slots=True)
class ValidatedProgram:
    slot_count: int
    code: bytes
    instructions: tuple
    by_address: dict


def encode(slot_count, code):
    """Serialize a trusted compiler-produced code section."""
    # TODO: validate field ranges and form the exact big-endian header.
    raise NotImplementedError("implement bytecode encoding")


def validate(program):
    """Decode and verify an untrusted MNO1 binary before execution."""
    # TODO: perform structural decoding followed by control-flow/stack analysis.
    raise NotImplementedError("implement bytecode validation")
