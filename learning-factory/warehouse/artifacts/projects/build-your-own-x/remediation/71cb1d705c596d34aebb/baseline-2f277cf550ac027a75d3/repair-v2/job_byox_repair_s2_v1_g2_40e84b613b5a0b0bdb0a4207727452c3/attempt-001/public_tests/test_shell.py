#!/usr/bin/env python3
"""Public, implementation-agnostic contract checks for msh."""

import errno
import os
from pathlib import Path
import select
import signal
import sys
import tempfile
import time
import unittest

try:
    import pty
except ImportError:  # pragma: no cover - platform-dependent capability
    pty = None


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from public_tests.process_harness import run_process


SHELL_BIN = os.environ.get("MSH_BIN", "starter/msh")


def run_command(source, *, input_text=None, cwd=None, timeout=3):
    argv = [SHELL_BIN, "-c", source] if input_text is None else [SHELL_BIN]
    return run_process(
        argv,
        input=input_text,
        text=True,
        cwd=cwd,
        timeout=timeout,
        check=False,
    )


class ShellContractTests(unittest.TestCase):
    def test_blank_line_succeeds(self):
        result = run_command(" \t ")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_external_command_and_status(self):
        result = run_command("printf 'hello\\n'")
        self.assertEqual((result.returncode, result.stdout), (0, "hello\n"))
        result = run_command("/bin/sh -c 'exit 7'")
        self.assertEqual(result.returncode, 7)

    def test_quotes_escapes_and_empty_argument(self):
        result = run_command("printf '<%s><%s><%s>\\n' 'a b' c\\ d \"\"")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "<a b><c d><>\n")

    def test_pipeline(self):
        result = run_command("printf 'one\\ntwo\\n'|grep two|tr o O")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "twO\n")

    def test_redirection_and_append(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, "out")
            first = run_command(f"printf one > {target}")
            second = run_command(f"printf two >> {target}")
            third = run_command(f"cat < {target}")
            self.assertEqual([first.returncode, second.returncode, third.returncode], [0, 0, 0])
            self.assertEqual(third.stdout, "onetwo")

    def test_cd_persists_across_batch_lines(self):
        result = run_command("", input_text="cd /\n/bin/pwd\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "/\n")

    def test_missing_command_is_127(self):
        result = run_command("msh-command-that-does-not-exist")
        self.assertEqual(result.returncode, 127)
        self.assertIn("msh-command-that-does-not-exist", result.stderr)

    def test_syntax_error_launches_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory, "must-not-exist")
            result = run_command(f"touch {marker} |")
            self.assertEqual(result.returncode, 2)
            self.assertIn("syntax:", result.stderr)
            self.assertFalse(marker.exists())

    def test_parent_builtin_redirection_is_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, "jobs")
            result = run_command("", input_text=f"jobs > {target}\nprintf 'visible\\n'\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "visible\n")
            self.assertEqual(target.read_text(), "")

    def test_background_pipeline_jobs_and_fg(self):
        source = "/bin/sleep 0.2 | cat &\njobs\nfg %1\nprintf 'done\\n'\n"
        result = run_command("", input_text=source, timeout=4)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stderr, r"(?m)^\[1\] [0-9]+$")
        self.assertRegex(
            result.stdout,
            r"(?m)^\[1\] Running /bin/sleep 0\.2 \| cat &$",
        )
        self.assertTrue(result.stdout.endswith("done\n"))


def read_until(fd, marker, timeout=3):
    deadline = time.monotonic() + timeout
    data = bytearray()
    while marker not in data:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"PTY did not produce {marker!r}; got {bytes(data)!r}")
        readable, _, _ = select.select([fd], [], [], remaining)
        if not readable:
            continue
        try:
            chunk = os.read(fd, 4096)
        except OSError as error:
            if error.errno == errno.EIO:
                break
            raise
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def wait_for_child(child, timeout):
    deadline = time.monotonic() + timeout
    while True:
        try:
            waited, status = os.waitpid(child, os.WNOHANG)
        except InterruptedError:
            continue
        if waited == child:
            return status
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        time.sleep(min(0.02, remaining))


def pty_process_groups(master, child):
    groups = {child}
    try:
        foreground = os.tcgetpgrp(master)
        if foreground > 0:
            groups.add(foreground)
    except OSError:
        pass
    groups.discard(os.getpgrp())
    groups.discard(0)
    return groups


def terminate_pty_child(child, groups):
    status = wait_for_child(child, 0.10)
    if status is not None:
        return status
    for signal_number, timeout in ((signal.SIGTERM, 0.50), (signal.SIGKILL, 1.00)):
        for group in groups:
            try:
                os.killpg(group, signal_number)
            except ProcessLookupError:
                pass
        try:
            os.kill(child, signal_number)
        except ProcessLookupError:
            pass
        status = wait_for_child(child, timeout)
        if status is not None:
            return status
    return None


class InteractiveContractTests(unittest.TestCase):
    @unittest.skipUnless(pty is not None and os.name == "posix", "PTY unavailable")
    def test_foreground_terminal_interrupt_returns_to_prompt(self):
        try:
            child, master = pty.fork()
        except OSError as error:
            self.skipTest(f"PTY unavailable: {error}")
        if child == 0:
            binary = str(Path(SHELL_BIN).resolve())
            os.execv(binary, [binary])

        reaped = False
        try:
            self.assertIn(b"msh$ ", read_until(master, b"msh$ "))
            os.write(master, b"/bin/sleep 5\n")
            time.sleep(0.10)
            os.write(master, b"\x03")
            self.assertIn(b"msh$ ", read_until(master, b"msh$ "))
            os.write(master, b"exit 0\n")
            status = wait_for_child(child, 2.0)
            self.assertIsNotNone(status, "PTY shell did not exit before the deadline")
            reaped = status is not None
            self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        finally:
            groups = pty_process_groups(master, child)
            os.close(master)
            if not reaped:
                status = terminate_pty_child(child, groups)
                if status is None:
                    self.fail("PTY shell resisted bounded TERM/KILL cleanup")


if __name__ == "__main__":
    if not Path(SHELL_BIN).exists():
        raise SystemExit(f"MSH_BIN does not exist: {SHELL_BIN}")
    unittest.main(verbosity=2)
