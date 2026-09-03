#!/usr/bin/env python3
"""Deterministic validator-only tests for the sealed Pebble reference."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from environment.process_runner import CAPTURE_LIMIT, run


BINARY = Path(os.environ.get(
    "PEBBLE_BIN", str(ROOT / "sealed" / "reference" / "pebble"))).resolve()
CC = os.environ.get("CC", "cc")


class ReferenceTests(unittest.TestCase):
    maxDiff = None

    def eval_source(self, source, max_steps=None, stdout=None):
        with tempfile.TemporaryDirectory(prefix="pebble-reference-") as directory:
            source_path = Path(directory) / "program.pb"
            source_path.write_text(source, encoding="utf-8")
            argv = [str(BINARY), "eval"]
            if max_steps is not None:
                argv.extend(["--max-steps", str(max_steps)])
            argv.append(str(source_path))
            return run(argv, stdout=stdout)

    def compiled_source(self, source, stdout=None):
        with tempfile.TemporaryDirectory(prefix="pebble-reference-") as directory:
            temporary = Path(directory)
            source_path = temporary / "program.pb"
            assembly_path = temporary / "program.s"
            executable_path = temporary / "program"
            source_path.write_text(source, encoding="utf-8")
            generated = run([
                str(BINARY), "compile", str(source_path), "-o", str(assembly_path)
            ])
            self.assertEqual((generated.returncode, generated.stdout, generated.stderr),
                             (0, "", ""))
            linked = run([CC, str(assembly_path), "-o", str(executable_path)])
            self.assertEqual((linked.returncode, linked.stdout, linked.stderr),
                             (0, "", ""))
            return run([str(executable_path)], stdout=stdout)

    def assert_differential(self, source):
        interpreted = self.eval_source(source)
        compiled = self.compiled_source(source)
        self.assertEqual(
            (compiled.returncode, compiled.stdout, compiled.stderr),
            (interpreted.returncode, interpreted.stdout, interpreted.stderr),
        )

    def test_arithmetic_associativity_and_signed_remainder(self):
        source = """
print 20 - 5 - 3;
print -7 / 3;
print -7 % 3;
print 2 + 3 * 4 == 14;
print 5 != 5;
"""
        result = self.eval_source(source)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, "12\n-2\n-1\n1\n0\n", ""))
        self.assert_differential(source)

    def test_nested_control_flow_is_equivalent(self):
        source = """
let outer = 3;
let value = 0;
while outer {
    if outer >= 2 { value = value * 10 + outer; }
    else { value = value + 7; }
    outer = outer - 1;
}
print value;
"""
        self.assert_differential(source)

    def test_all_runtime_failures_are_equivalent(self):
        programs = [
            "print 9223372036854775807 + 1;\n",
            "print 1 + (9223372036854775807 + 1);\n",
            "print (-9223372036854775807 - 1) / -1;\n",
            "print (-9223372036854775807 - 1) % -1;\n",
            "print 10 / 0;\n",
            "while 1 {}\n",
        ]
        for source in programs:
            with self.subTest(source=source):
                interpreted = self.eval_source(source)
                self.assertEqual(interpreted.returncode, 70)
                self.assertTrue(interpreted.stderr.startswith("runtime error:"))
                self.assert_differential(source)

    def test_step_budget_boundary(self):
        source = "let n = 1; while n { n = 0; } print 7;\n"
        exhausted = self.eval_source(source, max_steps=4)
        self.assertEqual((exhausted.returncode, exhausted.stdout, exhausted.stderr),
                         (70, "", "runtime error: step limit exceeded\n"))
        exact = self.eval_source(source, max_steps=5)
        self.assertEqual((exact.returncode, exact.stdout, exact.stderr),
                         (0, "7\n", ""))

    def test_static_name_errors(self):
        cases = [
            ("let x = x;\n", "unknown variable 'x'"),
            ("let x = 1; let x = 2;\n", "duplicate variable 'x'"),
            ("let x = 1; let x = missing;\n", "duplicate variable 'x'"),
            ("x = 1;\n", "unknown variable 'x'"),
            ("print x; let x = 1;\n", "declarations are allowed only"),
        ]
        for source, fragment in cases:
            with self.subTest(source=source):
                result = self.eval_source(source)
                self.assertEqual(result.returncode, 65)
                self.assertIn(fragment, result.stderr)

    def test_lexer_and_parser_locations(self):
        cases = [
            ("\nprint 9223372036854775808;\n", "2:7: integer literal"),
            ("print 1\n", "2:1: expected ';'"),
            ("print @;\n", "1:7: unexpected byte 0x40"),
            ("let if = 1;\n", "1:5: expected identifier"),
        ]
        for source, fragment in cases:
            with self.subTest(source=source):
                result = self.eval_source(source)
                self.assertEqual(result.returncode, 65)
                self.assertIn(fragment, result.stderr)

    def test_expression_and_block_depth_limits(self):
        parentheses = "(" * 129 + "1" + ")" * 129
        expression_result = self.eval_source("print " + parentheses + ";\n")
        self.assertEqual(expression_result.returncode, 65)
        self.assertIn("expression nesting exceeds", expression_result.stderr)

        block_source = "if 1 {" * 129 + "print 1;" + "}" * 129
        block_result = self.eval_source(block_source)
        self.assertEqual(block_result.returncode, 65)
        self.assertIn("block nesting exceeds", block_result.stderr)

    def test_variable_limit(self):
        source = "".join("let v%d = %d;\n" % (index, index)
                         for index in range(257))
        result = self.eval_source(source)
        self.assertEqual(result.returncode, 65)
        self.assertIn("program exceeds 256 variables", result.stderr)

    def test_failed_compile_preserves_existing_output(self):
        with tempfile.TemporaryDirectory(prefix="pebble-reference-") as directory:
            temporary = Path(directory)
            source_path = temporary / "invalid.pb"
            output_path = temporary / "existing.s"
            source_path.write_text("print unknown;\n", encoding="utf-8")
            output_path.write_text("sentinel\n", encoding="utf-8")
            result = run([
                str(BINARY), "compile", str(source_path), "-o", str(output_path)
            ])
            self.assertEqual(result.returncode, 65)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "sentinel\n")
            self.assertEqual(list(temporary.glob("existing.s.tmp.*")), [])

    def test_cli_and_missing_input_statuses(self):
        usage = run([str(BINARY), "eval", "--max-steps", "0", "anything.pb"])
        self.assertEqual(usage.returncode, 64)
        self.assertTrue(usage.stderr.startswith("usage:"))
        missing = run([str(BINARY), "eval", "/definitely/not/a/pebble/file"])
        self.assertEqual(missing.returncode, 66)
        self.assertIn("I/O error:", missing.stderr)

    def test_standard_output_failure_is_io_error_in_both_backends(self):
        source = "print 1234567890;\n"
        full_device = Path("/dev/full")
        if not full_device.exists():
            self.skipTest("/dev/full is unavailable")
        with full_device.open("wb", buffering=0) as sink:
            interpreted = self.eval_source(source, stdout=sink)
            compiled = self.compiled_source(source, stdout=sink)
        expected_error = "I/O error: cannot write standard output\n"
        self.assertEqual((interpreted.returncode, interpreted.stderr),
                         (66, expected_error))
        self.assertEqual((compiled.returncode, compiled.stderr),
                         (66, expected_error))

        read_descriptor, write_descriptor = os.pipe()
        os.close(read_descriptor)
        with os.fdopen(write_descriptor, "wb", buffering=0) as sink:
            interpreted = self.eval_source(source, stdout=sink)
            compiled = self.compiled_source(source, stdout=sink)
        self.assertEqual((interpreted.returncode, interpreted.stderr),
                         (66, expected_error))
        self.assertEqual((compiled.returncode, compiled.stderr),
                         (66, expected_error))

    def test_process_runner_caps_retained_output(self):
        program = (
            "import os\n"
            "data = b'x' * 131072\n"
            "while data:\n"
            "    data = data[os.write(1, data):]\n"
        )
        result = run([sys.executable, "-c", program], timeout=2.0)
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertEqual(len(result.stdout.encode("utf-8")), CAPTURE_LIMIT)
        self.assertTrue(result.stdout_truncated)

    def test_timeout_kills_pipe_holding_descendant(self):
        helper = ROOT / "sealed" / "reference_tests" / "process_tree_helper.py"
        with tempfile.TemporaryDirectory(prefix="pebble-containment-") as directory:
            ready = Path(directory) / "ready"
            escaped = Path(directory) / "escaped"
            with self.assertRaises(subprocess.TimeoutExpired):
                run([sys.executable, str(helper), str(ready), str(escaped)],
                    timeout=0.2)
            self.assertTrue(ready.is_file())
            time.sleep(1.1)
            self.assertFalse(escaped.exists())


if __name__ == "__main__":
    if not BINARY.is_file():
        raise SystemExit("missing reference binary: %s" % BINARY)
    unittest.main(verbosity=2)
