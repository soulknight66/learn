#!/usr/bin/env python3
"""Deterministic unit coverage for the worker-controlled process boundary."""

import os
import stat
import sys
import time
import unittest

from environment.harness import (
    ProcessResult,
    ProcessTimeout,
    readonly_source,
    run_process,
    sanitized_environment,
)
from public_tests import run_tests as public_suite


class HarnessTests(unittest.TestCase):
    def test_captured_logs_are_bounded_while_pipes_are_drained(self):
        script = (
            "import sys; "
            "sys.stdout.write('o' * 4096); sys.stdout.flush(); "
            "sys.stderr.write('e' * 4096); sys.stderr.flush()"
        )
        result = run_process(
            [sys.executable, "-c", script], timeout=2, max_output_bytes=128
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout), 128)
        self.assertEqual(len(result.stderr), 128)
        self.assertTrue(result.stdout_truncated)
        self.assertTrue(result.stderr_truncated)

    def test_nonzero_status_and_output_are_preserved(self):
        script = "import sys; print('out'); sys.stderr.write('err\\n'); sys.exit(7)"
        result = run_process([sys.executable, "-c", script], timeout=2)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout, "out\n")
        self.assertEqual(result.stderr, "err\n")

    def test_source_and_attempt_directory_are_read_only(self):
        with readonly_source("print 1;\n", prefix="mica-harness-mode-") as item:
            directory, path = item
            self.assertEqual(stat.S_IMODE(os.stat(directory).st_mode), 0o555)
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o444)
            script = "import io, sys; io.open(sys.argv[1], 'w').write('changed')"
            result = run_process(
                [sys.executable, "-c", script, path],
                timeout=2,
                cwd=directory,
                env=sanitized_environment(directory),
            )
            self.assertNotEqual(result.returncode, 0)
            with open(path, "r", encoding="ascii") as handle:
                self.assertEqual(handle.read(), "print 1;\n")

    @unittest.skipUnless(os.name == "posix", "requires POSIX process groups")
    def test_timeout_signals_and_reaps_descendant_group(self):
        child_script = "import time; time.sleep(30)"
        parent_script = (
            "import signal, subprocess, sys, time\n"
            "child = subprocess.Popen([sys.executable, '-c', {!r}])\n"
            "def stop(signum, frame):\n"
            "    child.wait(timeout=1)\n"
            "    sys.exit(0)\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            "print(child.pid)\n"
            "sys.stdout.flush()\n"
            "while True:\n"
            "    time.sleep(1)\n"
        ).format(child_script)
        with self.assertRaises(ProcessTimeout) as raised:
            run_process(
                [sys.executable, "-c", parent_script],
                timeout=0.3,
                group_grace_seconds=0.5,
            )
        child_pid = int(raised.exception.stdout.strip())
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                os.kill(child_pid, 0)
            except OSError:
                break
            time.sleep(0.01)
        else:
            self.fail("descendant process still exists after group cleanup")


class PublicAcceptanceRegressionTests(unittest.TestCase):
    def test_overflow_acceptance_rejects_stdout_even_with_runtime_exit(self):
        case = public_suite.MicaCliTests(
            methodName="test_arithmetic_domain_is_checked"
        )
        path = "/attempt/input.mica"

        def invoke(source):
            return (
                ProcessResult(
                    ["mica", path],
                    70,
                    "unexpected output\n",
                    path + ":1:18: runtime: overflow\n",
                ),
                path,
            )

        case.invoke = invoke
        with self.assertRaises(AssertionError):
            case.test_arithmetic_domain_is_checked()


if __name__ == "__main__":
    unittest.main(verbosity=2)
