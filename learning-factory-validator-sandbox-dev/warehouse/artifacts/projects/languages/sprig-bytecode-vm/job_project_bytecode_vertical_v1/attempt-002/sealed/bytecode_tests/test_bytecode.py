from __future__ import annotations

import unittest

from tinyvm.compiler import compile_program
from tinyvm.parser import parse
from tinyvm.vm import execute


class BytecodeContractTests(unittest.TestCase):
    def test_control_flow_targets_are_resolved_and_in_range(self) -> None:
        program = compile_program(parse("let x = 2; while (x) { x = x - 1; } print x;"))
        for instruction in program.instructions:
            if instruction.opcode.startswith("JUMP"):
                self.assertIsInstance(instruction.operand, int)
                self.assertGreaterEqual(instruction.operand, 0)
                self.assertLess(instruction.operand, len(program.instructions))
        self.assertEqual((0,), execute(program).outputs)

    def test_compiler_emits_halt_and_vm_rejects_unknown_opcode(self) -> None:
        from tinyvm.compiler import BytecodeProgram, Instruction
        from tinyvm.model import RuntimeFault
        program = compile_program(parse("print 1;"))
        self.assertEqual("HALT", program.instructions[-1].opcode)
        with self.assertRaisesRegex(RuntimeFault, "unknown opcode"):
            execute(BytecodeProgram((Instruction("MYSTERY"), Instruction("HALT"))))

    def test_verifier_rejects_malformed_operands_and_instructions(self) -> None:
        from tinyvm.compiler import BytecodeProgram, Instruction
        from tinyvm.model import RuntimeFault
        malformed = (
            ("boolean CONST", (Instruction("CONST", True), Instruction("PRINT"), Instruction("HALT"))),
            ("boolean jump", (Instruction("JUMP", True), Instruction("HALT"))),
            ("spurious operand", (Instruction("HALT", "ignored"),)),
            ("raw object", (object(),)),
            ("stack underflow", (Instruction("PRINT"), Instruction("HALT"))),
            ("unreachable instruction", (Instruction("JUMP", 1), Instruction("HALT"), Instruction("HALT"))),
            (
                "inconsistent join",
                (
                    Instruction("CONST", 1), Instruction("JUMP_IF_FALSE", 3),
                    Instruction("CONST", 2), Instruction("HALT"),
                ),
            ),
        )
        for name, instructions in malformed:
            with self.subTest(name=name), self.assertRaises(RuntimeFault):
                execute(BytecodeProgram(instructions))

    def test_compiler_metering_matches_source_semantics(self) -> None:
        program = compile_program(parse("print 1;"))
        self.assertEqual(2, [item.opcode for item in program.instructions].count("TICK"))
        self.assertEqual(2, execute(program, max_steps=2).steps)

    def test_short_circuit_has_branch_not_eager_boolean_opcode(self) -> None:
        program = compile_program(parse("print false && missing;"))
        opcodes = [instruction.opcode for instruction in program.instructions]
        self.assertIn("JUMP_IF_FALSE", opcodes)
        self.assertEqual((0,), execute(program).outputs)


if __name__ == "__main__":
    unittest.main()
