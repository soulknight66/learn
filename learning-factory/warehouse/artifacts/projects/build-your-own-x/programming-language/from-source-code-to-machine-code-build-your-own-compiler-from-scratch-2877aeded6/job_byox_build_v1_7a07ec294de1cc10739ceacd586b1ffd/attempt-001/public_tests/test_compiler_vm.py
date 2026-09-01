import io
import struct
import unittest

from minnow import FormatError, SemanticError, StepLimitExceeded, compile_source, run_bytecode, run_source


class CompilerVmTests(unittest.TestCase):
    def run_program(self, source, *, step_limit=1_000_000):
        output = io.StringIO()
        run_source(source, output, step_limit=step_limit)
        return output.getvalue()

    def test_arithmetic_and_truth(self):
        output = self.run_program("print 2 + 3 * 4; print !0; print 7 / -3; print 7 % -3;")
        self.assertEqual(output, "14\n1\n-2\n1\n")

    def test_scope_shadowing_and_assignment(self):
        source = """
            let x = 4;
            if (x) {
                let x = 9;
                x = x + 1;
                print x;
            } else { print 99; }
            print x;
        """
        self.assertEqual(self.run_program(source), "10\n4\n")

    def test_while_loop(self):
        source = "let n = 3; while (n > 0) { print n; n = n - 1; }"
        self.assertEqual(self.run_program(source), "3\n2\n1\n")

    def test_binary_header_has_exact_declared_length(self):
        binary = compile_source("let x = 1; print x;")
        self.assertEqual(binary[:4], b"MNO1")
        self.assertEqual(struct.unpack(">I", binary[6:10])[0], len(binary) - 10)

    def test_undefined_assignment_is_semantic_error(self):
        with self.assertRaises(SemanticError):
            compile_source("missing = 1;")

    def test_malformed_binary_is_rejected_before_output(self):
        output = io.StringIO()
        # PRINT underflows, even though a HALT follows it.
        malformed = b"MNO1" + struct.pack(">HI", 0, 2) + bytes([0x30, 0xFF])
        with self.assertRaises(FormatError):
            run_bytecode(malformed, output)
        self.assertEqual(output.getvalue(), "")

    def test_step_limit_stops_valid_infinite_loop(self):
        binary = compile_source("while (true) {}")
        with self.assertRaises(StepLimitExceeded):
            run_bytecode(binary, io.StringIO(), step_limit=20)


if __name__ == "__main__":
    unittest.main()
