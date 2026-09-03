#!/usr/bin/env python3
"""Bounded parser and resource-boundary regression cases."""

import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
BINARY = str(Path(os.environ.get("MSH_BIN", ROOT / "sealed/reference/msh")).resolve())


def invoke(source, timeout=3):
    return subprocess.run(
        [BINARY, "-c", source],
        text=True,
        capture_output=True,
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

    def test_over_limit_batch_line_is_rejected(self):
        source = "x" * (1024 * 1024 + 1) + "\n"
        result = subprocess.run(
            [BINARY],
            input=source,
            text=True,
            capture_output=True,
            timeout=4,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("exceeds 1 MiB", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
