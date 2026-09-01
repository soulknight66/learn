#!/usr/bin/env python3
"""Sealed semantic boundary tests for the reference executable."""

import os
import subprocess
import unittest


PEBBLE_BIN = os.environ.get("PEBBLE_BIN", "../reference/build/pebble")


def run(source):
    return subprocess.run(
        [PEBBLE_BIN, "-e", source],
        check=False,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
    )


class ReferenceBoundaryTests(unittest.TestCase):
    def assert_run(self, source, output):
        result = run(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, output)
        self.assertEqual(result.stderr, "")

    def assert_compile_error(self, source):
        result = run(source)
        self.assertEqual(result.returncode, 65)
        self.assertEqual(result.stdout, "")
        self.assertRegex(result.stderr, r"^\d+:\d+: .+\n$")

    def assert_runtime_error(self, source, word):
        result = run(source)
        self.assertEqual(result.returncode, 70)
        self.assertIn(word, result.stderr.lower())

    def test_integer_maximum(self):
        self.assert_run("print 9223372036854775807;", "9223372036854775807\n")

    def test_literal_above_maximum(self):
        self.assert_compile_error("print 9223372036854775808;")

    def test_addition_overflow(self):
        self.assert_runtime_error("print 9223372036854775807 + 1;", "overflow")

    def test_subtraction_overflow(self):
        self.assert_runtime_error("print (-9223372036854775807 - 1) - 1;", "overflow")

    def test_multiplication_overflow(self):
        self.assert_runtime_error("print 3037000500 * 3037000500;", "overflow")

    def test_minimum_divided_by_negative_one(self):
        self.assert_runtime_error("let m=-9223372036854775807-1; print m / -1;", "overflow")

    def test_minimum_remainder_negative_one(self):
        self.assert_runtime_error("let m=-9223372036854775807-1; print m % -1;", "overflow")

    def test_negating_minimum(self):
        self.assert_runtime_error("let m=-9223372036854775807-1; print -m;", "overflow")

    def test_left_associativity(self):
        self.assert_run("print 20 / 5 / 2; print 10 - 3 - 2;", "2\n5\n")

    def test_chained_short_circuit(self):
        self.assert_run(
            "print 0 && (1/0) && (1/0); print 1 || (1/0) || (1/0);",
            "0\n1\n",
        )

    def test_initializer_sees_outer_binding(self):
        self.assert_run("let x=5; { let x=x+2; print x; } print x;", "7\n5\n")

    def test_initializer_cannot_see_itself(self):
        self.assert_compile_error("{ let x=x; }")

    def test_name_leaves_scope(self):
        self.assert_compile_error("{ let local=1; } print local;")

    def test_keyword_prefix_is_identifier(self):
        self.assert_run("let printable=8; let iffy=9; print printable+iffy;", "17\n")

    def test_lone_boolean_operator_is_rejected(self):
        self.assert_compile_error("print 1 & 2;")

    def test_missing_brace_is_rejected(self):
        self.assert_compile_error("if (1) { print 1;")

    def test_carriage_return_and_newline_position(self):
        result = run("print 1;\r\nprint nope;")
        self.assertEqual(result.returncode, 65)
        self.assertTrue(result.stderr.startswith("2:7:"), result.stderr)

    def test_empty_comments(self):
        self.assert_run("// only a comment", "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
