#!/usr/bin/env python3
"""Deterministic tests for the public runner's subprocess containment."""

from __future__ import print_function

import os
import sys
import tempfile
import time
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from process_control import (CAPTURE_LIMIT, SuiteBudgetExpired, SuiteDeadline,
                             run_bounded)  # noqa: E402


@unittest.skipUnless(hasattr(os, "fork"), "POSIX fork is required")
class ProcessControlTests(unittest.TestCase):

    def test_expired_aggregate_deadline_blocks_next_case(self):
        deadline = SuiteDeadline(1.0)
        deadline._deadline = 0.0
        with self.assertRaises(SuiteBudgetExpired):
            deadline.case_timeout(1.0)

    def test_timeout_kills_descendant_before_it_can_write(self):
        program = (
            "import os,sys,time\n"
            "child=os.fork()\n"
            "if child == 0:\n"
            "    time.sleep(0.8)\n"
            "    open(sys.argv[1], 'w').write('escaped')\n"
            "    os._exit(0)\n"
            "time.sleep(10)\n"
        )
        with tempfile.TemporaryDirectory(prefix=".process-control-", dir=ROOT) as directory:
            marker = os.path.join(directory, "timeout-marker")
            result = run_bounded([sys.executable, "-c", program, marker], 0.2, directory)
            self.assertTrue(result.timed_out)
            time.sleep(1.0)
            self.assertFalse(os.path.exists(marker))

    def test_normal_parent_exit_still_cleans_descendant(self):
        program = (
            "import os,sys,time\n"
            "child=os.fork()\n"
            "if child == 0:\n"
            "    time.sleep(0.8)\n"
            "    open(sys.argv[1], 'w').write('escaped')\n"
            "    os._exit(0)\n"
            "os._exit(0)\n"
        )
        with tempfile.TemporaryDirectory(prefix=".process-control-", dir=ROOT) as directory:
            marker = os.path.join(directory, "exit-marker")
            result = run_bounded([sys.executable, "-c", program, marker], 2.0, directory)
            self.assertFalse(result.timed_out)
            self.assertEqual(0, result.returncode)
            time.sleep(1.0)
            self.assertFalse(os.path.exists(marker))

    def test_capture_is_bounded(self):
        program = "import os\nos.write(1, b'x' * {})\n".format(CAPTURE_LIMIT * 2)
        with tempfile.TemporaryDirectory(prefix=".process-control-", dir=ROOT) as directory:
            result = run_bounded([sys.executable, "-c", program], 2.0, directory)
            self.assertLessEqual(len(result.stdout.encode("utf-8")), CAPTURE_LIMIT)
            self.assertTrue(result.stdout_truncated)


if __name__ == "__main__":
    unittest.main()
