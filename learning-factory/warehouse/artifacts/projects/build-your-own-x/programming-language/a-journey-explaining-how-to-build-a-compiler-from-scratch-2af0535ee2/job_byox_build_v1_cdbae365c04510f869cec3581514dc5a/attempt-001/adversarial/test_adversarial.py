#!/usr/bin/env python3
"""Deterministic hostile-input checks; this is not a fuzzer."""

import os
import subprocess
import tempfile
import unittest


PEBBLE_BIN = os.environ.get("PEBBLE_BIN", "sealed/reference/build/pebble")


def run_eval(source, timeout=5):
    return subprocess.run(
        [PEBBLE_BIN, "-e", source],
        check=False,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


class AdversarialCases(unittest.TestCase):
    def test_very_long_integer_is_one_compile_error(self):
        result = run_eval("print " + ("9" * 10000) + ";")
        self.assertEqual(result.returncode, 65)
        self.assertEqual(result.stdout, "")
        self.assertLess(len(result.stderr), 256)

    def test_compile_error_prevents_earlier_print(self):
        result = run_eval("print 1; print never_declared;")
        self.assertEqual(result.returncode, 65)
        self.assertEqual(result.stdout, "")

    def test_runtime_error_preserves_prior_output(self):
        result = run_eval("print 1; print 1/0;")
        self.assertEqual(result.returncode, 70)
        self.assertEqual(result.stdout, "1\n")

    def test_operator_fragments_terminate(self):
        for source in ("print 1 & 1;", "print 1 | 1;", "print === 1;", "print !!;"):
            with self.subTest(source=source):
                self.assertEqual(run_eval(source).returncode, 65)

    def test_deep_but_bounded_grouping(self):
        source = "print " + ("(" * 128) + "7" + (")" * 128) + ";"
        result = run_eval(source)
        self.assertEqual((result.returncode, result.stdout), (0, "7\n"))

    def test_step_budget_stops_infinite_loop(self):
        result = run_eval("while (1) { }")
        self.assertEqual(result.returncode, 70)
        self.assertIn("step limit", result.stderr.lower())

    def test_file_over_one_mebibyte_is_rejected(self):
        path = None
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False) as stream:
                path = stream.name
                stream.write(b" " * (1048576 + 1))
            result = subprocess.run(
                [PEBBLE_BIN, path],
                check=False,
                universal_newlines=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            self.assertEqual(result.returncode, 74)
            self.assertIn("1 MiB", result.stderr)
        finally:
            if path is not None:
                os.unlink(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
