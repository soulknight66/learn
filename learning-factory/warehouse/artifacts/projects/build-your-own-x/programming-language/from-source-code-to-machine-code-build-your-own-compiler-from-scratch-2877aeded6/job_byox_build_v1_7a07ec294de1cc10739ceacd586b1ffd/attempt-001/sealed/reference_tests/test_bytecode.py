import io
from pathlib import Path
import struct
import unittest

from minnow import FormatError, compile_source, run_bytecode
from minnow.bytecode import Opcode, encode, validate


def binary(code, slots=0, *, declared=None, magic=b"MNO1"):
    length = len(code) if declared is None else declared
    return magic + struct.pack(">HI", slots, length) + bytes(code)


def const(value):
    return bytes([Opcode.CONST]) + struct.pack(">q", value)


def jump(opcode, destination):
    return bytes([opcode]) + struct.pack(">I", destination)


class BytecodeTests(unittest.TestCase):
    def assert_rejected_without_output(self, payload):
        output = io.StringIO()
        with self.assertRaises(FormatError):
            run_bytecode(payload, output)
        self.assertEqual(output.getvalue(), "")

    def test_compiler_output_validates(self):
        payload = compile_source("let x = 3; while (x) { print x; x = x - 1; }")
        verified = validate(payload)
        self.assertEqual(verified.slot_count, 1)
        self.assertIs(verified.instructions[-1].opcode, Opcode.HALT)

    def test_hand_encoded_valid_program(self):
        payload = binary(const(-12) + bytes([Opcode.PRINT, Opcode.HALT]))
        output = io.StringIO()
        run_bytecode(payload, output)
        self.assertEqual(output.getvalue(), "-12\n")

    def test_header_failures(self):
        cases = (
            b"",
            binary(bytes([Opcode.HALT]), magic=b"NOPE"),
            binary(bytes([Opcode.HALT]), declared=2),
            binary(bytes([Opcode.HALT])) + b"trailing",
        )
        for payload in cases:
            with self.subTest(payload=payload):
                self.assert_rejected_without_output(payload)

    def test_published_hex_cases_are_rejected(self):
        case_directory = Path(__file__).resolve().parents[2] / "adversarial/cases"
        for path in sorted(case_directory.glob("*.hex")):
            with self.subTest(case=path.name):
                self.assert_rejected_without_output(bytes.fromhex(path.read_text(encoding="ascii")))

    def test_decode_failures(self):
        cases = (
            binary(bytes([0x77, Opcode.HALT])),
            binary(bytes([Opcode.CONST, 0, Opcode.HALT])),
            binary(bytes([Opcode.LOAD, 0, 0, Opcode.HALT]), slots=0),
        )
        for payload in cases:
            with self.subTest(payload=payload):
                self.assert_rejected_without_output(payload)

    def test_jump_must_target_instruction_boundary(self):
        payload = binary(jump(Opcode.JUMP, 1) + bytes([Opcode.HALT]))
        self.assert_rejected_without_output(payload)

    def test_underflow_and_nonempty_halt_are_rejected(self):
        self.assert_rejected_without_output(binary(bytes([Opcode.PRINT, Opcode.HALT])))
        self.assert_rejected_without_output(binary(const(1) + bytes([Opcode.HALT])))

    def test_inconsistent_merge_depth_is_rejected(self):
        code = (
            const(1)
            + jump(Opcode.JUMP_IF_FALSE, 28)
            + const(2)
            + jump(Opcode.JUMP, 28)
            + bytes([Opcode.HALT])
        )
        self.assertEqual(len(code), 29)
        self.assert_rejected_without_output(binary(code))

    def test_unreachable_instruction_is_rejected(self):
        code = jump(Opcode.JUMP, 6) + bytes([Opcode.NOT, Opcode.HALT])
        self.assert_rejected_without_output(binary(code))

    def test_halt_rules_are_enforced(self):
        for code in (b"", bytes([Opcode.NOT]), bytes([Opcode.HALT, Opcode.HALT])):
            with self.subTest(code=code):
                self.assert_rejected_without_output(binary(code))

    def test_encode_checks_host_arguments(self):
        self.assertEqual(encode(0, bytes([Opcode.HALT])), binary(bytes([Opcode.HALT])))
        for slots in (-1, 65536):
            with self.subTest(slots=slots), self.assertRaises(ValueError):
                encode(slots, b"")
        with self.assertRaises(TypeError):
            encode(True, b"")
        with self.assertRaises(TypeError):
            encode(0, "bytes")


if __name__ == "__main__":
    unittest.main()
