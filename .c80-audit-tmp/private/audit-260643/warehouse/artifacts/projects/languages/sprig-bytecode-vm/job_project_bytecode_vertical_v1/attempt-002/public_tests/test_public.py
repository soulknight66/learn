from __future__ import annotations

import unittest

import tinyvm


class PublicContractTests(unittest.TestCase):
    def test_arithmetic_precedence_and_left_associativity(self) -> None:
        result = tinyvm.run_source("print 2 + 3 * 4; print 20 - 5 - 3;")
        self.assertEqual((14, 12), result.outputs)

    def test_state_loop_and_branch(self) -> None:
        source = """
            let total = 0;
            let n = 5;
            while (n > 0) { total = total + n; n = n - 1; }
            if (total == 15) { print total; } else { print 0; }
        """
        result = tinyvm.run_source(source)
        self.assertEqual((15,), result.outputs)
        self.assertEqual({"n": 0, "total": 15}, result.globals)
        self.assertGreater(result.steps, 0)

    def test_boolean_results_and_short_circuit(self) -> None:
        result = tinyvm.run_source("print false && (1 / 0); print true || missing;")
        self.assertEqual((0, 1), result.outputs)

    def test_comments_and_unary(self) -> None:
        result = tinyvm.run_source("// ignored\nprint -(2 + 3); print !0;")
        self.assertEqual((-5, 1), result.outputs)

    def test_errors_are_typed(self) -> None:
        with self.assertRaises(tinyvm.ParseError):
            tinyvm.run_source("print 1")
        with self.assertRaises(tinyvm.RuntimeFault):
            tinyvm.run_source("print unknown;")

    def test_budget_bounds_nontermination(self) -> None:
        with self.assertRaises(tinyvm.ResourceLimit):
            tinyvm.run_source("while (true) { print 1; }", max_steps=25)


if __name__ == "__main__":
    unittest.main()
