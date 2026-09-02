#!/usr/bin/env python3
"""Maintainer-only black-box tests for the complete Sprig reference."""

from __future__ import print_function

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import unittest


BINARY = None


def invoke(arguments):
    process = subprocess.Popen(
        arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=4)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise AssertionError("reference process exceeded the 4 second timeout")
    return process.returncode, stdout, stderr


def run_source(source, mode=None):
    if isinstance(source, str):
        source = source.encode("ascii")
    with tempfile.TemporaryDirectory(prefix="sprig-reference-") as directory:
        path = os.path.join(directory, "case.sprig")
        with open(path, "wb") as output:
            output.write(source)
        arguments = [BINARY]
        if mode is not None:
            arguments.append(mode)
        arguments.append(path)
        return invoke(arguments)


class ReferenceLanguageTests(unittest.TestCase):
    def assert_success(self, source, expected):
        code, stdout, stderr = run_source(source)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, expected)
        self.assertEqual(stderr, "")

    def assert_error(self, source, code, fragment, expected_stdout=""):
        actual, stdout, stderr = run_source(source)
        self.assertEqual(actual, code)
        self.assertEqual(stdout, expected_stdout)
        self.assertIn("error", stderr.lower())
        self.assertIn(fragment, stderr.lower())

    def test_empty_and_comments(self):
        self.assert_success("\r\n # only a comment", "")

    def test_precedence_parentheses_and_associativity(self):
        self.assert_success(
            "print 2 + 3 * 4;\n"
            "print (2 + 3) * 4;\n"
            "print 20 - 5 - 3;\n",
            "14\n20\n12\n",
        )

    def test_negative_division_truncates_toward_zero(self):
        self.assert_success("print -7 / 2; print 7 / -2;\n", "-3\n-3\n")

    def test_recursive_unary(self):
        self.assert_success("print ---5; print --5;\n", "-5\n5\n")

    def test_bindings_are_resolved(self):
        self.assert_success(
            "let first = 9; let second = first + 2; print second * first;",
            "99\n",
        )

    def test_maximum_literal_and_computed_minimum(self):
        self.assert_success(
            "print 9223372036854775807;\n"
            "print -9223372036854775807 - 1;\n",
            "9223372036854775807\n-9223372036854775808\n",
        )

    def test_lexical_failures(self):
        self.assert_error("print 9223372036854775808;", 65, "literal exceeds")
        self.assert_error("print @;", 65, "unexpected byte")
        self.assert_error("let abcdefghijklmnopqrstuvwxyzabcdef = 1;", 65,
                          "identifier exceeds")

    def test_syntax_failures(self):
        self.assert_error("1 + 2;", 65, "expected 'let' or 'print'")
        self.assert_error("print (1 + 2;", 65, "expected ')'")
        self.assert_error("print ;", 65, "expected expression")
        self.assert_error("let = 2;", 65, "expected identifier")
        self.assert_error("print 2", 65, "expected ';'")

    def test_name_failures(self):
        self.assert_error("print nope;", 65, "undefined identifier")
        self.assert_error("let self = self + 1;", 65, "undefined identifier")
        self.assert_error("let x = 1; let x = 2;", 65, "duplicate declaration")

    def test_variable_boundary(self):
        declarations = ["let v%d = %d;" % (i, i) for i in range(64)]
        self.assert_success("".join(declarations) + "print v63;", "63\n")
        self.assert_error("".join(declarations) + "let extra = 1;", 65,
                          "variable limit")

    def test_instruction_limit(self):
        source = "print " + "+".join(["1"] * 513) + ";"
        self.assert_error(source, 65, "instruction limit")

    def test_expression_nesting_boundary(self):
        allowed = "(" * 512 + "1" + ")" * 512
        rejected = "(" * 513 + "1" + ")" * 513
        self.assert_success("print " + allowed + ";", "1\n")
        self.assert_error("print " + rejected + ";", 65, "nesting limit")

    def test_arithmetic_runtime_failures(self):
        self.assert_error("print 1 / 0;", 70, "division by zero")
        self.assert_error("print 9223372036854775807 + 1;", 70,
                          "overflow in addition")
        self.assert_error("print (-9223372036854775807 - 1) - 1;", 70,
                          "overflow in subtraction")
        self.assert_error("print 9223372036854775807 * 2;", 70,
                          "overflow in multiplication")
        self.assert_error("print -(-9223372036854775807 - 1);", 70,
                          "overflow in negation")
        self.assert_error("print (-9223372036854775807 - 1) / -1;", 70,
                          "overflow in division")

    def test_runtime_error_preserves_prior_output(self):
        self.assert_error("print 7; print 1 / 0;", 70, "division by zero", "7\n")

    def test_stack_limit(self):
        expression = "1"
        for unused in range(260):
            expression = "1+(" + expression + ")"
        self.assert_error("print " + expression + ";", 70, "stack overflow")

    def test_tokens_include_eof_location(self):
        code, stdout, stderr = run_source("print x;\n", "--tokens")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            stdout,
            "1:1 PRINT\n1:7 IDENTIFIER x\n1:8 SEMICOLON\n2:1 EOF\n",
        )

    def test_disassembly_order_and_locations(self):
        code, stdout, stderr = run_source("print 2+3;", "--disassemble")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            stdout,
            "0000 CONST 2 @ 1:7\n"
            "0001 CONST 3 @ 1:9\n"
            "0002 ADD   @ 1:8\n"
            "0003 PRINT @ 1:1\n"
            "0004 HALT  @ 1:11\n",
        )

    def test_source_size_limit(self):
        self.assert_error(b" " * (1024 * 1024 + 1), 74, "exceeds 1 mib")

    def test_usage_and_missing_file_exit_codes(self):
        code, stdout, stderr = invoke([BINARY])
        self.assertEqual((code, stdout), (64, ""))
        self.assertIn("usage", stderr.lower())
        missing = os.path.join(tempfile.gettempdir(),
                               "sprig-file-that-does-not-exist")
        code, stdout, stderr = invoke([BINARY, missing])
        self.assertEqual((code, stdout), (74, ""))
        self.assertIn("cannot open", stderr.lower())


def main():
    global BINARY
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    options = parser.parse_args()
    BINARY = os.path.abspath(options.binary)
    if not os.path.isfile(BINARY):
        parser.error("binary does not exist: " + BINARY)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        ReferenceLanguageTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
