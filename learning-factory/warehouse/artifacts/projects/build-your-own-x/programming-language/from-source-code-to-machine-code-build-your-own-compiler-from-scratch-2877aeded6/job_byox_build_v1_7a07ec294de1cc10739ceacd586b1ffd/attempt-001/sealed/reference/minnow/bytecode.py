"""MNO1 binary encoding and whole-program structural verification."""

from collections import deque
from dataclasses import dataclass
from enum import IntEnum
import struct

from .errors import FormatError


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


OPERANDS = {
    Opcode.CONST: (8, ">q"),
    Opcode.LOAD: (2, ">H"),
    Opcode.STORE: (2, ">H"),
    Opcode.JUMP: (4, ">I"),
    Opcode.JUMP_IF_FALSE: (4, ">I"),
}

BINARY = {
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
}

UNARY = {Opcode.NEG, Opcode.NOT}


def encode(slot_count, code):
    if isinstance(slot_count, bool) or not isinstance(slot_count, int):
        raise TypeError("slot_count must be an integer")
    if not 0 <= slot_count <= 65535:
        raise ValueError("slot_count is outside u16 range")
    if not isinstance(code, (bytes, bytearray)):
        raise TypeError("code must be bytes or bytearray")
    payload = bytes(code)
    if len(payload) > 0xFFFFFFFF:
        raise ValueError("code section is outside u32 range")
    return MAGIC + struct.pack(">HI", slot_count, len(payload)) + payload


def _decode(code, slot_count):
    instructions = []
    address = 0
    while address < len(code):
        raw_opcode = code[address]
        try:
            opcode = Opcode(raw_opcode)
        except ValueError as exc:
            raise FormatError(f"unknown opcode 0x{raw_opcode:02x} at code offset {address}", code="FORMAT004") from exc
        operand = None
        operand_width = 0
        if opcode in OPERANDS:
            operand_width, layout = OPERANDS[opcode]
            end = address + 1 + operand_width
            if end > len(code):
                raise FormatError(f"truncated {opcode.name} at code offset {address}", code="FORMAT005")
            operand = struct.unpack_from(layout, code, address + 1)[0]
        size = 1 + operand_width
        if opcode in (Opcode.LOAD, Opcode.STORE) and operand >= slot_count:
            raise FormatError(f"slot {operand} is outside slot count {slot_count}", code="FORMAT006")
        instructions.append(Instruction(address, opcode, operand, size))
        address += size
    return instructions


def _stack_rule(opcode):
    if opcode in (Opcode.CONST, Opcode.LOAD):
        return 0, 1
    if opcode in (Opcode.STORE, Opcode.PRINT, Opcode.JUMP_IF_FALSE):
        return 1, -1
    if opcode in BINARY:
        return 2, -1
    if opcode in UNARY:
        return 1, 0
    return 0, 0


def _successors(instruction, code_length):
    next_address = instruction.address + instruction.size
    if instruction.opcode is Opcode.HALT:
        return ()
    if instruction.opcode is Opcode.JUMP:
        return (instruction.operand,)
    if instruction.opcode is Opcode.JUMP_IF_FALSE:
        if next_address >= code_length:
            raise FormatError("conditional branch can fall through past code", code="FORMAT010")
        if instruction.operand == next_address:
            return (next_address,)
        return (instruction.operand, next_address)
    if next_address >= code_length:
        raise FormatError("instruction can fall through past code", code="FORMAT010")
    return (next_address,)


def _verify_flow(instructions, by_address, code_length):
    for instruction in instructions:
        if instruction.opcode in (Opcode.JUMP, Opcode.JUMP_IF_FALSE) and instruction.operand not in by_address:
            raise FormatError(
                f"jump from {instruction.address} does not target an instruction boundary",
                code="FORMAT007",
            )

    depths = {0: 0}
    pending = deque([0])
    while pending:
        address = pending.popleft()
        instruction = by_address[address]
        depth = depths[address]
        required, change = _stack_rule(instruction.opcode)
        if depth < required:
            raise FormatError(f"stack underflow at code offset {address}", code="FORMAT008")
        if instruction.opcode is Opcode.HALT and depth != 0:
            raise FormatError("HALT requires an empty stack", code="FORMAT009")
        outgoing_depth = depth + change
        if outgoing_depth > 65535:
            raise FormatError("stack depth exceeds 65,535", code="FORMAT011")
        for successor in _successors(instruction, code_length):
            known = depths.get(successor)
            if known is not None and known != outgoing_depth:
                raise FormatError(f"inconsistent stack depth at code offset {successor}", code="FORMAT012")
            if known is None:
                depths[successor] = outgoing_depth
                pending.append(successor)

    if len(depths) != len(instructions):
        unreachable = sorted(set(by_address).difference(depths))[0]
        raise FormatError(f"unreachable instruction at code offset {unreachable}", code="FORMAT013")


def validate(program):
    if not isinstance(program, bytes):
        raise TypeError("program must be bytes")
    if len(program) < HEADER_SIZE:
        raise FormatError("binary is shorter than the MNO1 header", code="FORMAT001")
    if program[:4] != MAGIC:
        raise FormatError("invalid MNO1 magic", code="FORMAT002")
    slot_count, declared_length = struct.unpack(">HI", program[4:HEADER_SIZE])
    code = program[HEADER_SIZE:]
    if declared_length != len(code):
        raise FormatError("declared code length does not match file length", code="FORMAT003")

    instructions = _decode(code, slot_count)
    if not instructions or instructions[-1].opcode is not Opcode.HALT:
        raise FormatError("code must end with HALT", code="FORMAT014")
    if any(item.opcode is Opcode.HALT for item in instructions[:-1]):
        raise FormatError("HALT may appear only as the final instruction", code="FORMAT014")

    by_address = {item.address: item for item in instructions}
    _verify_flow(instructions, by_address, len(code))
    return ValidatedProgram(slot_count, code, tuple(instructions), by_address)
