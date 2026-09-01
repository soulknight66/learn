#!/usr/bin/env python3
"""Deterministic black-box checks for the bytehist command."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SUBMISSION_ROOT = Path(__file__).resolve().parent.parent
BINARY = SUBMISSION_ROOT / "build" / "bytehist"
SCRATCH_ROOT = SUBMISSION_ROOT / "build" / "test-tmp"


class BytehistCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BINARY.is_file():
            raise RuntimeError(f"missing test subject: {BINARY}")
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)

    def run_bytehist(self, arguments=(), input_bytes=b"", cwd=SCRATCH_ROOT):
        return subprocess.run(
            [str(BINARY), *arguments],
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            check=False,
            timeout=10,
        )

    def assert_success(self, completed, expected_stdout):
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, expected_stdout)
        self.assertEqual(completed.stderr, b"")

    def test_empty_standard_input(self):
        completed = self.run_bytehist(input_bytes=b"")
        self.assert_success(completed, b"total 0\n")

    def test_ordinary_standard_input_has_exact_order_and_format(self):
        completed = self.run_bytehist(input_bytes=b"banana\n")
        expected = b"total 7\n0A 1\n61 3\n62 1\n6E 2\n"
        self.assert_success(completed, expected)

    def test_binary_file_includes_high_bytes(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as directory:
            path = Path(directory) / "binary-input"
            path.write_bytes(bytes((0x00, 0x0A, 0x7F, 0x80, 0xFF, 0x80)))
            completed = self.run_bytehist((str(path),), cwd=directory)

        expected = b"total 6\n00 1\n0A 1\n7F 1\n80 2\nFF 1\n"
        self.assert_success(completed, expected)

    def test_single_hyphen_is_a_literal_file_name(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as directory:
            Path(directory, "-").write_bytes(b"\xff")
            completed = self.run_bytehist(("-",), cwd=directory)

        self.assert_success(completed, b"total 1\nFF 1\n")

    def test_too_many_arguments_has_exact_usage_failure(self):
        completed = self.run_bytehist(("first", "second"))
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, b"")
        self.assertEqual(completed.stderr, b"usage: bytehist [INPUT]\n")

    def test_unavailable_input_path_fails_before_report(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as directory:
            missing = Path(directory) / "not-present"
            completed = self.run_bytehist((str(missing),), cwd=directory)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, b"")
        self.assertTrue(completed.stderr.startswith(b"bytehist:"))

    def test_non_regular_input_failure_emits_no_report(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH_ROOT) as directory:
            input_directory = Path(directory) / "input-directory"
            input_directory.mkdir()
            completed = self.run_bytehist(
                (str(input_directory),), cwd=directory
            )

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, b"")
        self.assertTrue(completed.stderr.startswith(b"bytehist:"))

    def test_lengths_around_two_processing_boundaries(self):
        cases = (4095, 4097, 8191, 8193)
        for length in cases:
            with self.subTest(length=length):
                completed = self.run_bytehist(
                    input_bytes=bytes((0xA5,)) * length
                )
                expected = f"total {length}\nA5 {length}\n".encode("ascii")
                self.assert_success(completed, expected)

    @unittest.skipUnless(hasattr(os, "pipe"), "requires anonymous pipes")
    def test_closed_output_pipe_is_reported_as_failure(self):
        read_end, write_end = os.pipe()
        os.close(read_end)
        try:
            completed = subprocess.run(
                [str(BINARY)],
                stdin=subprocess.DEVNULL,
                stdout=write_end,
                stderr=subprocess.PIPE,
                cwd=SCRATCH_ROOT,
                check=False,
                timeout=10,
            )
        finally:
            os.close(write_end)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stderr, b"bytehist: output failed\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
