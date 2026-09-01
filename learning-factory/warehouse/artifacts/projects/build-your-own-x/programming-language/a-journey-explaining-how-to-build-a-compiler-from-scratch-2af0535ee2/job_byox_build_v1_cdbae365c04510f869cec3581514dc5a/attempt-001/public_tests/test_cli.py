#!/usr/bin/env python3
"""Black-box conformance tests for the Pebble command-line interface."""

import os
import re
import subprocess
import tempfile
import unittest


PEBBLE_BIN = os.environ.get("PEBBLE_BIN", "starter/build/pebble")


def run_source(source):
    return subprocess.run(
        [PEBBLE_BIN, "-e", source],
        check=False,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
    )


class PebbleCliTests(unittest.TestCase):
    def test_empty_program(self):
        result = run_source("")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_precedence_and_unary(self):
        result = run_source("print 1 + 2 * 3; print -(8 - 3); print !0;")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "7\n-5\n1\n", ""))

    def test_scope_and_shadowing(self):
        source = "let x = 3; { let x = 9; print x; } x = x + 1; print x;"
        result = run_source(source)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "9\n4\n", ""))

    def test_loop_and_branch(self):
        source = "let n=6; let p=1; while(n>1){p=p*n;n=n-1;} if(p==720){print p;}else{print 0;}"
        result = run_source(source)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "720\n", ""))

    def test_short_circuit_and_boolean_normalization(self):
        result = run_source("print 0 && (1 / 0); print 8 || (1 / 0); print 2 && 7;")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "0\n1\n1\n", ""))

    def test_comments_comparisons_and_remainder(self):
        source = "// ignored\nprint 7 % 4; print 3 <= 3; print 4 != 4;"
        result = run_source(source)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "3\n1\n0\n", ""))

    def test_unknown_name_is_compile_error(self):
        result = run_source("print missing;")
        self.assertEqual(result.returncode, 65)
        self.assertEqual(result.stdout, "")
        self.assertRegex(result.stderr, r"^1:\d+: .+\n$")

    def test_same_scope_duplicate_is_compile_error(self):
        result = run_source("let x=1; let x=2;")
        self.assertEqual(result.returncode, 65)
        self.assertIn("duplicate", result.stderr.lower())

    def test_division_by_zero_is_runtime_error(self):
        result = run_source("print 4 / 0;")
        self.assertEqual(result.returncode, 70)
        self.assertEqual(result.stdout, "")
        self.assertIn("zero", result.stderr.lower())

    def test_file_mode(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as stream:
            stream.write("print 42;\n")
            path = stream.name
        try:
            result = subprocess.run(
                [PEBBLE_BIN, path], check=False, universal_newlines=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5,
            )
        finally:
            os.unlink(path)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "42\n", ""))

    def test_usage(self):
        result = subprocess.run(
            [PEBBLE_BIN], check=False, universal_newlines=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5,
        )
        self.assertEqual(result.returncode, 64)
        self.assertEqual(result.stdout, "")
        self.assertTrue(re.fullmatch(r"usage: .+\n", result.stderr))


if __name__ == "__main__":
    unittest.main(verbosity=2)
