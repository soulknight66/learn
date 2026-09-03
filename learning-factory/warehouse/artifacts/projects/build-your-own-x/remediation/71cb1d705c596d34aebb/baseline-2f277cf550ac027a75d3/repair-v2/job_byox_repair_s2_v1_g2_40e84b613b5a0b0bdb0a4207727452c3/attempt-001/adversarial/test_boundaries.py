#!/usr/bin/env python3
"""Bounded parser and resource-boundary regression cases."""

import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from public_tests.process_harness import run_process


BINARY = str(Path(os.environ.get("MSH_BIN", ROOT / "sealed/reference/msh")).resolve())


def invoke(source, timeout=3):
    return run_process(
        [BINARY, "-c", source],
        text=True,
        timeout=timeout,
        check=False,
    )


class BoundaryTests(unittest.TestCase):
    def test_operator_runs_do_not_crash_or_hang(self):
        alphabet = ["|", "&", "<", ">", ">>"]
        cases = []
        for left in alphabet:
            for right in alphabet:
                cases.append(f"true {left} {right} true")
        for source in cases:
            with self.subTest(source=source):
                result = invoke(source)
                self.assertGreaterEqual(result.returncode, 0)
                self.assertLessEqual(result.returncode, 255)

    def test_thousand_arguments(self):
        result = invoke("true " + " ".join(f"a{i}" for i in range(1000)))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_many_empty_fragments_form_one_empty_argument(self):
        result = invoke("printf '<%s>\\n' " + "''" * 1000)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "<>\n")

    def test_exact_limit_is_accepted_with_or_without_delimiter(self):
        source = b"true" + b" " * (1024 * 1024 - 4)
        for suffix in (b"", b"\n"):
            with self.subTest(delimited=bool(suffix)):
                result = run_process(
                    [BINARY],
                    input=source + suffix,
                    timeout=4,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_over_limit_batch_line_is_rejected(self):
        source = "x" * (1024 * 1024 + 1) + "\n"
        result = run_process(
            [BINARY],
            input=source,
            text=True,
            timeout=4,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("exceeds 1 MiB", result.stderr)


class ProcessHarnessTests(unittest.TestCase):
    def test_timeout_terminates_same_group_descendant(self):
        target = (
            "import os, pathlib, sys, time\n"
            "child = os.fork()\n"
            "if child == 0:\n"
            "    time.sleep(10)\n"
            "else:\n"
            "    pathlib.Path(sys.argv[1]).write_text("
            "f'{child} {os.getpgrp()}')\n"
            "    time.sleep(10)\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            identity_file = Path(directory, "identity")
            started = time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):
                run_process(
                    [sys.executable, "-c", target, str(identity_file)],
                    timeout=0.3,
                    check=False,
                )
            elapsed = time.monotonic() - started
            child_pid, process_group = map(int, identity_file.read_text().split())
            self.assertLess(elapsed, 2.5)
            try:
                os.kill(child_pid, 0)
            except ProcessLookupError:
                descendant_alive = False
            else:
                descendant_alive = True
                try:
                    os.killpg(process_group, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self.assertFalse(descendant_alive, "timed-out descendant survived cleanup")


if __name__ == "__main__":
    unittest.main(verbosity=2)
