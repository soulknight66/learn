#!/usr/bin/env python3
"""Boundary-focused tests intended for validator-controlled execution."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get(
    "PEBBLE_BIN", str(ROOT / "sealed" / "reference" / "pebble"))).resolve()
MAX_SOURCE = 1024 * 1024


def run(argv, timeout=5.0):
    return subprocess.run(
        argv,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=timeout,
    )


class AdversarialTests(unittest.TestCase):
    def eval_bytes(self, payload):
        with tempfile.TemporaryDirectory(prefix="pebble-adversarial-") as directory:
            source = Path(directory) / "input.pb"
            source.write_bytes(payload)
            return run([str(BINARY), "eval", str(source)])

    def test_exact_source_limit_is_accepted(self):
        payload = b"#" + b"x" * (MAX_SOURCE - 1)
        result = self.eval_bytes(payload)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_one_byte_over_source_limit_is_rejected(self):
        payload = b"#" + b"x" * MAX_SOURCE
        result = self.eval_bytes(payload)
        self.assertEqual(result.returncode, 65)
        self.assertIn("source exceeds 1048576 bytes", result.stderr)

    def test_embedded_nul_and_utf8_are_lexical_errors(self):
        for payload, fragment in [
                (b"print 1;\x00print 2;", "unexpected byte 0x00"),
                ("print café;".encode("utf-8"), "unexpected byte 0xc3")]:
            with self.subTest(payload=payload):
                result = self.eval_bytes(payload)
                self.assertEqual(result.returncode, 65)
                self.assertIn(fragment, result.stderr)

    def test_deep_flat_expression_is_rejected_before_execution(self):
        source = "print " + "+".join("1" for _ in range(140)) + ";\n"
        result = self.eval_bytes(source.encode("ascii"))
        self.assertEqual(result.returncode, 65)
        self.assertIn("expression tree exceeds 128 levels", result.stderr)

    def test_unary_depth_is_rejected_by_parser(self):
        source = "print " + "!" * 129 + "0;\n"
        result = self.eval_bytes(source.encode("ascii"))
        self.assertEqual(result.returncode, 65)
        self.assertIn("expression nesting exceeds 128", result.stderr)

    def test_declaration_inside_dead_branch_is_still_rejected(self):
        result = self.eval_bytes(b"if 0 { let hidden = 1; }\n")
        self.assertEqual(result.returncode, 65)
        self.assertIn("declarations are allowed only", result.stderr)

    def test_failed_publish_removes_temporary_sibling(self):
        with tempfile.TemporaryDirectory(prefix="pebble-adversarial-") as directory:
            temporary = Path(directory)
            source = temporary / "valid.pb"
            destination = temporary / "destination"
            source.write_text("print 1;\n", encoding="utf-8")
            destination.mkdir()
            result = run([
                str(BINARY), "compile", str(source), "-o", str(destination)
            ])
            self.assertEqual(result.returncode, 66)
            self.assertTrue(destination.is_dir())
            self.assertEqual(list(temporary.glob("destination.tmp.*")), [])


if __name__ == "__main__":
    if not BINARY.is_file():
        raise SystemExit("missing reference binary: %s" % BINARY)
    unittest.main(verbosity=2)
