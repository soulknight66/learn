#!/usr/bin/env python3
"""Sealed edge-case tests for the Mica command-line contract."""

import os
import subprocess
import tempfile
import unittest


MICA_BIN = os.environ.get(
    "MICA_BIN",
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "reference", "bin", "mica")
    ),
)


class ReferenceEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(MICA_BIN) or not os.access(MICA_BIN, os.X_OK):
            raise AssertionError("MICA_BIN must name an executable regular file: {}".format(MICA_BIN))

    def invoke(self, source, option=None, timeout=5):
        with tempfile.TemporaryDirectory(prefix="mica-sealed-") as directory:
            path = os.path.join(directory, "case.mica")
            with open(path, "w", encoding="ascii", newline="") as handle:
                handle.write(source)
            argv = [MICA_BIN]
            if option:
                argv.append(option)
            argv.append(path)
            result = subprocess.run(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=timeout,
            )
            return result, path

    def assert_success(self, source, stdout):
        result, _ = self.invoke(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, stdout)
        self.assertEqual(result.stderr, "")

    def assert_phase_error(self, source, phase, line, column, exit_code):
        result, path = self.invoke(source)
        self.assertEqual(result.returncode, exit_code)
        self.assertEqual(result.stdout, "")
        prefix = "{}:{}:{}: {}:".format(path, line, column, phase)
        self.assertTrue(result.stderr.startswith(prefix), result.stderr)

    def test_empty_and_comment_only_programs(self):
        self.assert_success("", "")
        self.assert_success("# no instructions follow", "")

    def test_left_associativity(self):
        self.assert_success("print 20 - 5 - 3; print 100 / 5 / 2;\n", "12\n10\n")

    def test_all_ordering_operators(self):
        source = "print 2 < 3; print 3 <= 3; print 4 > 5; print 5 >= 5;\n"
        self.assert_success(source, "1\n1\n0\n1\n")

    def test_nested_unary_is_right_associative(self):
        self.assert_success("print ---4; print !!9; print !-0;\n", "-4\n1\n1\n")

    def test_identifier_keyword_prefixes_are_names(self):
        self.assert_success("let printable = 8; let trueish = 9; print printable + trueish;\n", "17\n")

    def test_leading_zero_literal_retains_lexeme(self):
        result, _ = self.invoke("print 0000000042;\n", option="--tokens")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1:7 INTEGER 0000000042\n", result.stdout)

    def test_integer_above_domain_is_lex_error(self):
        self.assert_phase_error("print 1000000001;\n", "lex", 1, 7, 65)

    def test_unknown_byte_after_crlf_has_byte_location(self):
        self.assert_phase_error("print 1;\r\n@", "lex", 2, 1, 65)

    def test_assignment_to_unknown_name_is_compile_error(self):
        self.assert_phase_error("value = 3;\n", "compile", 1, 1, 65)

    def test_redeclaration_across_blocks_is_compile_error(self):
        source = "let value = 1; if true { let value = 2; }\n"
        self.assert_phase_error(source, "compile", 1, 30, 65)

    def test_unknown_name_in_unreachable_code_is_rejected(self):
        self.assert_phase_error("halt; print never_declared;\n", "compile", 1, 13, 65)

    def test_slot_is_zero_when_declaration_statement_did_not_execute(self):
        self.assert_success("if false { let delayed = 7; } print delayed;\n", "0\n")

    def test_runtime_output_is_not_rolled_back(self):
        result, path = self.invoke("print 7; print 1 / 0;\n")
        self.assertEqual(result.returncode, 70)
        self.assertEqual(result.stdout, "7\n")
        self.assertTrue(result.stderr.startswith(path + ":1:18: runtime:"), result.stderr)

    def test_multiplication_domain_boundary(self):
        self.assert_success("print 1000000 * 1000;\n", "1000000000\n")
        self.assert_phase_error("print 1000001 * 1000;\n", "runtime", 1, 15, 70)

    def test_empty_infinite_loop_hits_instruction_limit(self):
        result, path = self.invoke("while true { }\n", timeout=5)
        self.assertEqual(result.returncode, 70)
        self.assertEqual(result.stdout, "")
        self.assertIn(": runtime: instruction limit exceeded", result.stderr)
        self.assertTrue(result.stderr.startswith(path + ":"), result.stderr)

    def test_bytecode_jump_targets_are_patched(self):
        source = "if false { print 1; } else { print 2; }\n"
        result, _ = self.invoke(source, option="--bytecode")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(" -1 @", result.stdout)
        self.assertIn("JUMP_IF_FALSE", result.stdout)
        self.assertIn("JUMP", result.stdout)

    def test_usage_and_missing_file_exit_codes(self):
        usage = subprocess.run(
            [MICA_BIN],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=5,
        )
        self.assertEqual(usage.returncode, 64)
        self.assertEqual(usage.stdout, "")

        with tempfile.TemporaryDirectory(prefix="mica-missing-") as directory:
            missing = os.path.join(directory, "absent.mica")
            io_result = subprocess.run(
                [MICA_BIN, missing],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=5,
            )
        self.assertEqual(io_result.returncode, 66)
        self.assertEqual(io_result.stdout, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
