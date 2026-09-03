#!/usr/bin/env python3
"""Transparent black-box smoke tests for the Pebble command-line contract."""

import os
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from environment.process_runner import run


DEFAULT_BINARY = ROOT / "starter" / "pebble"
BINARY = Path(os.environ.get("PEBBLE_BIN", str(DEFAULT_BINARY))).resolve()
CC = os.environ.get("CC", "cc")


class PebbleSmokeTests(unittest.TestCase):
    maxDiff = None

    def eval_source(self, source, *options):
        with tempfile.TemporaryDirectory(prefix="pebble-public-") as directory:
            path = Path(directory) / "case.pb"
            path.write_text(source, encoding="utf-8")
            return run([str(BINARY), "eval", *options, str(path)])

    def test_precedence_and_unary(self) -> None:
        result = self.eval_source("print 2 + 3 * 4; print (2 + 3) * 4; print !0;\n")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "14\n20\n1\n", ""))

    def test_variables_loop_and_comment(self) -> None:
        source = """# triangular number
let n = 5;
let total = 0;
while n > 0 { total = total + n; n = n - 1; }
print total;
"""
        result = self.eval_source(source)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "15\n", ""))

    def test_conditional(self) -> None:
        result = self.eval_source("let x = 7; if x <= 7 { print 11; } else { print 22; }\n")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "11\n", ""))

    def test_unknown_variable_is_static_error(self) -> None:
        result = self.eval_source("print missing;\n")
        self.assertEqual(result.returncode, 65)
        self.assertIn("unknown variable", result.stderr)

    def test_division_by_zero_is_runtime_error(self) -> None:
        result = self.eval_source("print 9 / 0;\n")
        self.assertEqual(result.returncode, 70)
        self.assertIn("runtime error:", result.stderr)

    def test_compile_link_run(self) -> None:
        source = "let x = 6; let y = 7; print x * y;\n"
        with tempfile.TemporaryDirectory(prefix="pebble-public-") as directory:
            temporary = Path(directory)
            input_path = temporary / "case.pb"
            assembly_path = temporary / "case.s"
            executable_path = temporary / "case"
            input_path.write_text(source, encoding="utf-8")

            compiled = run([str(BINARY), "compile", str(input_path), "-o", str(assembly_path)])
            self.assertEqual((compiled.returncode, compiled.stderr), (0, ""))
            linked = run([CC, str(assembly_path), "-o", str(executable_path)])
            self.assertEqual((linked.returncode, linked.stderr), (0, ""))
            executed = run([str(executable_path)])
            self.assertEqual((executed.returncode, executed.stdout, executed.stderr), (0, "42\n", ""))


if __name__ == "__main__":
    if not BINARY.is_file():
        raise SystemExit(f"missing Pebble binary: {BINARY}; run make -C starter")
    unittest.main(verbosity=2)
