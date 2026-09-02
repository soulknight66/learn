import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import run_vectors


class BoundedRunnerTests(unittest.TestCase):
    def test_success_capture(self):
        result = run_vectors.run_bounded(
            [sys.executable, "-c", "print('captured')"], timeout_seconds=2.0
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "captured\n")
        self.assertEqual(result.stderr, "")

    def test_capture_is_bounded(self):
        result = run_vectors.run_bounded(
            [
                sys.executable,
                "-c",
                "import os; os.write(1, b'x' * 20000); os.write(2, b'y' * 20000)",
            ],
            timeout_seconds=2.0,
            capture_limit=1024,
        )
        self.assertLess(len(result.stdout), 1100)
        self.assertLess(len(result.stderr), 1100)
        self.assertIn("capture truncated", result.stdout)
        self.assertIn("capture truncated", result.stderr)

    def test_timeout_kills_started_descendant(self):
        helper = Path(__file__).with_name("timeout_process_tree_helper.py")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ready = root / "ready"
            escaped = root / "escaped"
            command = [
                sys.executable,
                str(helper),
                "--parent",
                "--ready",
                str(ready),
                "--escaped",
                str(escaped),
            ]
            with self.assertRaises(subprocess.TimeoutExpired) as context:
                run_vectors.run_bounded(command, timeout_seconds=1.0)

            self.assertTrue(ready.is_file())
            self.assertIn("DESCENDANT_READY", context.exception.output)
            time.sleep(1.6)
            self.assertFalse(escaped.exists())


if __name__ == "__main__":
    unittest.main()
