#!/usr/bin/env python3
"""Black-box public tests for a compiled Mica executable."""

import os
import sys
import unittest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from environment.harness import readonly_source, run_process, sanitized_environment


MICA_BIN = os.path.abspath(
    os.environ.get(
        "MICA_BIN",
        os.path.join(os.path.dirname(__file__), "..", "starter", "bin", "mica"),
    )
)


class MicaCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(MICA_BIN):
            raise AssertionError("MICA_BIN is not a regular file: {}".format(MICA_BIN))
        if not os.access(MICA_BIN, os.X_OK):
            raise AssertionError("MICA_BIN is not executable: {}".format(MICA_BIN))

    def invoke(self, source, option=None, timeout=5):
        with readonly_source(
            source, filename="input.mica", prefix="mica-public-"
        ) as attempt:
            directory, path = attempt
            argv = [MICA_BIN]
            if option is not None:
                argv.append(option)
            argv.append(path)
            completed = run_process(
                argv,
                timeout=timeout,
                cwd=directory,
                env=sanitized_environment(directory),
            )
            return completed, path

    def assert_run(self, source, expected_stdout):
        completed, _ = self.invoke(source)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, expected_stdout)
        self.assertEqual(completed.stderr, "")

    def test_precedence_and_parentheses(self):
        self.assert_run("print 2 + 3 * 4;\nprint (2 + 3) * 4;\n", "14\n20\n")

    def test_unary_and_comparisons_normalize_booleans(self):
        source = "print !0; print !7; print -3 < -2; print 3 == 3; print 3 != 3;\n"
        self.assert_run(source, "1\n0\n1\n1\n0\n")

    def test_loop_and_assignments(self):
        source = (
            "let n = 5; let acc = 1;\n"
            "while n > 1 { acc = acc * n; n = n - 1; }\n"
            "print acc;\n"
        )
        self.assert_run(source, "120\n")

    def test_if_else_comments_and_flat_block_scope(self):
        source = (
            "# declaration in a taken block remains a program-wide slot\n"
            "if true { let answer = 40 + 2; } else { print 999; }\n"
            "print answer;\n"
        )
        self.assert_run(source, "42\n")

    def test_division_and_remainder_truncate_toward_zero(self):
        self.assert_run("print -20 / 3; print -20 % 3; print 20 / -3;\n", "-6\n-2\n-6\n")

    def test_halt_skips_later_execution(self):
        self.assert_run("print 1; halt; print 2 / 0;\n", "1\n")

    def test_compile_error_for_unknown_name(self):
        completed, path = self.invoke("print missing;\n")
        self.assertEqual(completed.returncode, 65)
        self.assertEqual(completed.stdout, "")
        self.assertTrue(completed.stderr.startswith(path + ":1:7: compile:"), completed.stderr)

    def test_parse_error_has_location(self):
        completed, path = self.invoke("print (1 + 2;\n")
        self.assertEqual(completed.returncode, 65)
        self.assertEqual(completed.stdout, "")
        self.assertTrue(completed.stderr.startswith(path + ":1:13: parse:"), completed.stderr)

    def test_runtime_errors_have_distinct_exit(self):
        completed, path = self.invoke("print 10 / (3 - 3);\n")
        self.assertEqual(completed.returncode, 70)
        self.assertEqual(completed.stdout, "")
        self.assertTrue(completed.stderr.startswith(path + ":1:10: runtime:"), completed.stderr)

    def test_arithmetic_domain_is_checked(self):
        completed, path = self.invoke("print 1000000000 + 1;\n")
        self.assertEqual(completed.returncode, 70)
        self.assertEqual(completed.stdout, "")
        self.assertTrue(completed.stderr.startswith(path + ":1:18: runtime:"), completed.stderr)

    def test_token_listing_includes_eof(self):
        completed, _ = self.invoke("let x = 2;\n", option="--tokens")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "1:1 LET let\n1:5 IDENTIFIER x\n1:7 EQUAL =\n"
            "1:9 INTEGER 2\n1:10 SEMICOLON ;\n2:1 EOF <eof>\n",
        )

    def test_bytecode_listing_is_deterministic(self):
        completed, _ = self.invoke("let x = 2;\n", option="--bytecode")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout,
            "0000 CONST 2 @1:9\n0001 STORE 0 @1:5\n0002 HALT @2:1\n",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
