from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from pydocklet import InvalidProcess, ProcessRunner


class ProcessRunnerTests(unittest.TestCase):
    def test_captures_and_truncates_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = ProcessRunner(max_output_bytes=5).run(
                [sys.executable, "-c", "import sys; print('abcdefgh'); print('xy', file=sys.stderr)"],
                Path(temporary),
                timeout=2.0,
            )
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout, "[...]")
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 5)
        self.assertEqual(result.stderr, "xy\n")
        self.assertFalse(result.timed_out)

    def test_timeout_has_reserved_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = ProcessRunner().run(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                Path(temporary),
                timeout=0.05,
            )
        self.assertEqual(result.exit_code, 124)
        self.assertTrue(result.timed_out)

    def test_rejects_empty_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(InvalidProcess):
                ProcessRunner().run([], Path(temporary))


if __name__ == "__main__":
    unittest.main()
