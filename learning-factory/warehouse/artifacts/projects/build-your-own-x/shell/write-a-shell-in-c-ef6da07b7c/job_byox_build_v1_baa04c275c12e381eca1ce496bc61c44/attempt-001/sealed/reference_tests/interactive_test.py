#!/usr/bin/env python3
"""Bounded pseudo-terminal check for foreground process-group handoff."""

import argparse
import errno
import os
from pathlib import Path
import pty
import select
import signal
import time
import unittest


SHELL_PATH = None


def read_until(descriptor, marker, timeout):
    deadline = time.monotonic() + timeout
    data = b""
    while marker not in data:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError("timed out waiting for {!r}; received {!r}".format(marker, data))
        readable, _, _ = select.select([descriptor], [], [], remaining)
        if not readable:
            continue
        try:
            chunk = os.read(descriptor, 4096)
        except OSError as error:
            if error.errno == errno.EIO:
                break
            raise
        if not chunk:
            break
        data += chunk
    return data


class InteractiveJobControlTest(unittest.TestCase):
    def test_control_c_targets_foreground_group_and_shell_recovers(self):
        child_pid, descriptor = pty.fork()
        if child_pid == 0:
            os.execv(str(SHELL_PATH), [str(SHELL_PATH)])

        reaped = False
        try:
            initial = read_until(descriptor, b"msh$ ", 3.0)
            self.assertIn(b"msh$ ", initial)
            os.write(descriptor, b"sleep 5\n")
            time.sleep(0.15)
            started = time.monotonic()
            os.write(descriptor, b"\x03")
            interrupted = read_until(descriptor, b"msh$ ", 3.0)
            self.assertLess(time.monotonic() - started, 3.0)
            self.assertIn(b"msh$ ", interrupted)

            os.write(descriptor, b"printf interactive-ok\n")
            recovered = read_until(descriptor, b"msh$ ", 3.0)
            self.assertIn(b"interactive-ok", recovered)
            os.write(descriptor, b"exit 0\n")
            waited, status = os.waitpid(child_pid, 0)
            reaped = True
            self.assertEqual(waited, child_pid)
            self.assertTrue(os.WIFEXITED(status))
            self.assertEqual(os.WEXITSTATUS(status), 0)
        finally:
            os.close(descriptor)
            if not reaped:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    os.waitpid(child_pid, 0)
                except OSError:
                    pass


def main():
    global SHELL_PATH

    parser = argparse.ArgumentParser()
    parser.add_argument("--shell", required=True)
    known, remaining = parser.parse_known_args()
    SHELL_PATH = Path(known.shell).resolve()
    unittest.main(argv=[os.path.basename(__file__)] + remaining)


if __name__ == "__main__":
    main()
