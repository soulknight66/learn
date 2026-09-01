#!/usr/bin/env python3
"""One-time check for the pristine scaffold; not a conformance test."""

from __future__ import print_function

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "starter"


class PristineScaffoldSmokeTest(unittest.TestCase):
    def test_known_lexer_placeholder_is_reachable(self):
        with tempfile.TemporaryDirectory(prefix="minish-scaffold-") as temp:
            work = Path(temp) / "starter"
            shutil.copytree(STARTER, work)
            environment = os.environ.copy()
            environment["LC_ALL"] = "C"
            build = subprocess.run(
                [
                    "make", "clean", "all",
                    "CFLAGS=-std=c11 -Wall -Wextra -Wpedantic -Werror -g",
                ],
                cwd=str(work),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=30,
                env=environment,
            )
            self.assertEqual(0, build.returncode, build.stderr)
            result = subprocess.run(
                ["./minish", "-c", "   \nnot-implemented"],
                cwd=str(work),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=5,
                env=environment,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("tokenization is a TODO", result.stderr)


if __name__ == "__main__":
    unittest.main()
