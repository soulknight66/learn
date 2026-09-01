import io
import unittest

from minnow import (
    RuntimeFault,
    SemanticError,
    StepLimitExceeded,
    compile_source,
    run_bytecode,
    run_source,
)


class ExecutionTests(unittest.TestCase):
    def execute(self, source, **kwargs):
        output = io.StringIO()
        run_source(source, output, **kwargs)
        return output.getvalue()

    def test_all_arithmetic_and_comparison_operators(self):
        source = """
            print 7 + 3; print 7 - 3; print 7 * 3;
            print 7 / 3; print -7 / 3; print 7 / -3; print -7 / -3;
            print 7 % 3; print -7 % 3; print 7 % -3; print -7 % -3;
            print 2 == 2; print 2 != 2; print 1 < 2; print 2 <= 2;
            print 3 > 2; print 3 >= 4; print !0; print !9;
        """
        self.assertEqual(
            self.execute(source),
            "10\n4\n21\n2\n-2\n-2\n2\n1\n-1\n1\n-1\n1\n0\n1\n1\n1\n0\n1\n0\n",
        )

    def test_precedence_parentheses_and_left_associativity(self):
        self.assertEqual(self.execute("print 2 + 3 * 4; print (2 + 3) * 4; print 20 / 5 / 2;"), "14\n20\n2\n")

    def test_branches_and_loop(self):
        source = """
            let n = 4;
            let total = 0;
            while (n) { total = total + n; n = n - 1; }
            if (total == 10) { print total; } else { print 0; }
            if (false) { print 99; }
        """
        self.assertEqual(self.execute(source), "10\n")

    def test_shadowing_assignment_and_outer_self_initializer(self):
        source = """
            let x = 5;
            if (true) { let x = x + 1; x = x + 1; print x; }
            x = x + 10;
            print x;
        """
        self.assertEqual(self.execute(source), "7\n15\n")

    def test_duplicate_and_undefined_names_are_static_errors(self):
        cases = (
            "let x = 1; let x = 2;",
            "print x;",
            "x = 1;",
            "let x = x;",
            "if (true) { let y = 1; } print y;",
        )
        for source in cases:
            with self.subTest(source=source), self.assertRaises(SemanticError):
                compile_source(source)

    def test_same_name_in_sibling_scopes_is_legal(self):
        source = "if (true) { let x = 1; print x; } if (true) { let x = 2; print x; }"
        self.assertEqual(self.execute(source), "1\n2\n")

    def test_division_remainder_and_overflow_faults(self):
        cases = (
            "print 1 / 0;",
            "print 1 % 0;",
            "print 9223372036854775807 + 1;",
            "print -9223372036854775807 - 2;",
            "print 3037000500 * 3037000500;",
            "let x = -9223372036854775807 - 1; print -x;",
            "let x = -9223372036854775807 - 1; print x / -1;",
        )
        for source in cases:
            with self.subTest(source=source), self.assertRaises(RuntimeFault):
                self.execute(source)

    def test_bytearray_is_accepted_and_argument_types_are_checked(self):
        binary = bytearray(compile_source("print 1;"))
        output = io.StringIO()
        run_bytecode(binary, output)
        self.assertEqual(output.getvalue(), "1\n")
        with self.assertRaises(TypeError):
            compile_source(b"print 1;")
        with self.assertRaises(TypeError):
            run_bytecode("not bytes", io.StringIO())
        for limit in (True, 1.5, "2"):
            with self.subTest(limit=limit), self.assertRaises(TypeError):
                run_bytecode(binary, io.StringIO(), step_limit=limit)
        for limit in (0, -1):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                run_bytecode(binary, io.StringIO(), step_limit=limit)

    def test_step_limit_counts_halt_and_breaks_loop(self):
        binary = compile_source("")
        run_bytecode(binary, io.StringIO(), step_limit=1)
        binary = compile_source("print 1;")
        with self.assertRaises(StepLimitExceeded):
            run_bytecode(binary, io.StringIO(), step_limit=2)

    def test_infinite_loop_hits_limit(self):
        with self.assertRaises(StepLimitExceeded):
            self.execute("while (true) {}", step_limit=30)


if __name__ == "__main__":
    unittest.main()
