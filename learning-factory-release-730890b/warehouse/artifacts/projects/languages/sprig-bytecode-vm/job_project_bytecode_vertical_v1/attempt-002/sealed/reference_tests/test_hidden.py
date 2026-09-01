from __future__ import annotations

import unittest

import tinyvm


class WithheldContractTests(unittest.TestCase):
    def test_negative_division_and_remainder_truncate_toward_zero(self) -> None:
        result = tinyvm.run_source("print -7 / 3; print -7 % 3; print 7 % -3;")
        self.assertEqual((-2, -1, 1), result.outputs)

    def test_logical_precedence(self) -> None:
        result = tinyvm.run_source("print true || false && false; print 1 < 2 == true;")
        self.assertEqual((1, 1), result.outputs)

    def test_duplicate_declaration_and_assignment_before_declaration(self) -> None:
        with self.assertRaises(tinyvm.RuntimeFault):
            tinyvm.run_source("let x = 1; let x = 2;")
        with self.assertRaises(tinyvm.RuntimeFault):
            tinyvm.run_source("x = 2;")

    def test_overflow_is_not_host_integer_growth(self) -> None:
        with self.assertRaisesRegex(tinyvm.RuntimeFault, "overflow"):
            tinyvm.run_source("print 9223372036854775807 + 1;")

    def test_signed_minimum_literal_and_bounded_integer_diagnostics(self) -> None:
        self.assertEqual((-9223372036854775808,), tinyvm.run_source("print -9223372036854775808;").outputs)
        huge = "print " + "9" * 5_000 + ";"
        with self.assertRaisesRegex(tinyvm.ParseError, r"64-bit magnitude at 1:7"):
            tinyvm.run_source(huge)

    def test_documented_ascii_lexical_contract(self) -> None:
        for source in ("print ١;", "let café = 1;", "print ²;"):
            with self.subTest(source=source), self.assertRaises(tinyvm.LexError):
                tinyvm.run_source(source)

    def test_error_order_and_budget_are_architecture_neutral(self) -> None:
        with self.assertRaisesRegex(tinyvm.RuntimeFault, "division by zero"):
            tinyvm.run_source("let x = 1; let x = 1 / 0;")
        with self.assertRaisesRegex(tinyvm.RuntimeFault, "division by zero"):
            tinyvm.run_source("x = 1 / 0;")
        result = tinyvm.run_source("print 1;", max_steps=2)
        self.assertEqual((1,), result.outputs)
        self.assertEqual(2, result.steps)
        with self.assertRaises(tinyvm.ResourceLimit):
            tinyvm.run_source("print 1;", max_steps=1)

    def test_else_is_not_executed_after_true_branch(self) -> None:
        result = tinyvm.run_source("if (2) { print 7; } else { print 1 / 0; }")
        self.assertEqual((7,), result.outputs)

    def test_diagnostics_carry_location(self) -> None:
        with self.assertRaisesRegex(tinyvm.LexError, r"2:1"):
            tinyvm.run_source("print 1;\n@")

    def test_invalid_budget_rejected_before_execution(self) -> None:
        for value in (0, -1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                tinyvm.run_source("print 1;", max_steps=value)


if __name__ == "__main__":
    unittest.main()
