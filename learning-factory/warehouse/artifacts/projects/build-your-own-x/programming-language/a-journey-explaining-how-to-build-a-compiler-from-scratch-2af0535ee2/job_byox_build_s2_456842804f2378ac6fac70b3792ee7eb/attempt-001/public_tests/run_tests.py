#!/usr/bin/env python3
"""Black-box public tests for the Sprig command-line contract."""

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
        stdout, stderr = process.communicate(timeout=3)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise AssertionError("Sprig process exceeded the 3 second timeout")
    return process.returncode, stdout, stderr


def run_source(source, mode=None):
    if isinstance(source, str):
        source = source.encode("ascii")
    with tempfile.TemporaryDirectory(prefix="sprig-public-") as directory:
        path = os.path.join(directory, "case.sprig")
        with open(path, "wb") as output:
            output.write(source)
        arguments = [BINARY]
        if mode is not None:
            arguments.append(mode)
        arguments.append(path)
        return invoke(arguments)


class PublicContractTests(unittest.TestCase):
    def assert_success(self, source, expected):
        code, stdout, stderr = run_source(source)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(stdout, expected)
        self.assertEqual(stderr, "")

    def assert_compile_error(self, source, fragment):
        code, stdout, stderr = run_source(source)
        self.assertEqual(code, 65)
        self.assertEqual(stdout, "")
        self.assertIn("error", stderr.lower())
        self.assertIn(fragment, stderr.lower())

    def test_empty_program(self):
        self.assert_success("# nothing to execute\n", "")

    def test_token_mode_is_stable(self):
        code, stdout, stderr = run_source(
            "let value = 12;\nprint value;\n", "--tokens")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            stdout,
            "1:1 LET\n"
            "1:5 IDENTIFIER value\n"
            "1:11 EQUAL\n"
            "1:13 INTEGER 12\n"
            "1:15 SEMICOLON\n"
            "2:1 PRINT\n"
            "2:7 IDENTIFIER value\n"
            "2:12 SEMICOLON\n"
            "3:1 EOF\n",
        )
        self.assertEqual(stderr, "")

    def test_precedence(self):
        self.assert_success("print 2 + 3 * 4;\n", "14\n")

    def test_parentheses_and_unary(self):
        self.assert_success("print -(2 + 3) * 4;\n", "-20\n")

    def test_bindings_and_comments(self):
        self.assert_success(
            "let base = 10; # retained by slot\n"
            "let answer = base * 4 + 2;\n"
            "print answer;\n",
            "42\n",
        )

    def test_left_associativity(self):
        self.assert_success("print 20 - 5 - 3;\n", "12\n")

    def test_undefined_name_is_compile_error(self):
        self.assert_compile_error("print missing;\n", "undefined identifier")

    def test_missing_semicolon_is_compile_error(self):
        self.assert_compile_error("print 1\n", "expected ';'")

    def test_division_by_zero_is_runtime_error(self):
        code, stdout, stderr = run_source("print 8 / 0;\n")
        self.assertEqual(code, 70)
        self.assertEqual(stdout, "")
        self.assertIn("division by zero", stderr.lower())

    def test_disassembly_exposes_stack_order(self):
        code, stdout, stderr = run_source("print 2 + 3;\n", "--disassemble")
        self.assertEqual(code, 0, stderr)
        opcodes = [line.split()[1] for line in stdout.splitlines()]
        self.assertEqual(opcodes, ["CONST", "CONST", "ADD", "PRINT", "HALT"])


def main():
    global BINARY
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    options = parser.parse_args()
    BINARY = os.path.abspath(options.binary)
    if not os.path.isfile(BINARY):
        parser.error("binary does not exist: " + BINARY)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PublicContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
