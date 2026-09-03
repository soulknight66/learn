#!/usr/bin/env python3
"""Instructor-side black-box checks for the scoped reference shell."""

import errno
import os
from pathlib import Path
import pty
import re
import select
import signal
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
SHELL_BIN = str(Path(os.environ.get("MSH_BIN", ROOT / "sealed/reference/msh")).resolve())


def run(source=None, *, batch=None, cwd=None, env=None, timeout=4):
    argv = [SHELL_BIN] if batch is not None else [SHELL_BIN, "-c", source]
    return subprocess.run(
        argv,
        input=batch,
        text=True,
        capture_output=True,
        cwd=cwd,
        env=env,
        timeout=timeout,
        check=False,
    )


class ParserAndExecutionTests(unittest.TestCase):
    def test_adjacent_fragments_and_literal_expansion_characters(self):
        result = run("printf '<%s><%s><%s><%s>\\n' ab\"cd\"'' '$HOME' '*' ';'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "<abcd><$HOME><*><;>\n")

    def test_malformed_inputs_are_status_two(self):
        malformed = [
            "echo '",
            "echo \\",
            "| echo no",
            "echo no || cat",
            "echo no >",
            "echo no < a < b",
            "echo no & echo later",
            "> nowhere",
        ]
        for source in malformed:
            with self.subTest(source=source):
                result = run(source)
                self.assertEqual(result.returncode, 2)
                self.assertIn("syntax:", result.stderr)

    def test_pipeline_status_comes_from_last_stage(self):
        result = run("/bin/sh -c 'exit 7' | /bin/sh -c 'exit 3'")
        self.assertEqual(result.returncode, 3, result.stderr)

    def test_signal_status_mapping(self):
        result = run("/bin/sh -c 'kill -TERM $$'")
        self.assertEqual(result.returncode, 128 + signal.SIGTERM, result.stderr)

    def test_permission_error_is_126(self):
        with tempfile.TemporaryDirectory() as directory:
            program = Path(directory, "not-executable")
            program.write_text("placeholder\n")
            program.chmod(0o644)
            result = run(str(program))
            self.assertEqual(result.returncode, 126)
            self.assertIn(str(program), result.stderr)

    def test_redirection_overrides_pipe_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, "data")
            first = run(f"printf from-file > {target} | cat")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, "")
            self.assertEqual(target.read_text(), "from-file")

            second = run(f"printf from-pipe | cat < {target}")
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(second.stdout, "from-file")

    def test_long_pipeline_delivers_eof(self):
        stages = ["printf 'alpha\\nbeta\\n'"] + ["cat"] * 20 + ["grep beta"]
        result = run(" | ".join(stages), timeout=4)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "beta\n")

    def test_invalid_exit_does_not_terminate_batch(self):
        result = run(batch="exit nope\nprintf 'still-running\\n'\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "still-running\n")
        self.assertIn("numeric status", result.stderr)

    def test_valid_exit_terminates_batch(self):
        result = run(batch="exit 9\nprintf 'must-not-run\\n'\n")
        self.assertEqual(result.returncode, 9)
        self.assertEqual(result.stdout, "")

    def test_cd_uses_home_and_rejects_extra_operands(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = dict(os.environ)
            environment["HOME"] = directory
            result = run(batch="cd\n/bin/pwd\ncd / /tmp\n", env=environment)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, f"{directory}\n")
            self.assertIn("too many operands", result.stderr)

    def test_background_job_is_listed_and_fg_waits(self):
        result = run(batch="/bin/sleep 0.15 &\njobs\nfg %1\nprintf 'done\\n'\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stderr, r"\[1\] [0-9]+")
        self.assertRegex(result.stdout, r"(?m)^\[1\] Running /bin/sleep 0\.15 &$")
        self.assertTrue(result.stdout.endswith("done\n"))


def read_until(fd, marker, timeout=4):
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


class InteractiveJobControlTests(unittest.TestCase):
    def test_stop_list_resume_and_interrupt_foreground_job(self):
        child, master = pty.fork()
        if child == 0:
            os.execv(SHELL_BIN, [SHELL_BIN])

        reaped = False
        try:
            self.assertIn(b"msh$ ", read_until(master, b"msh$ "))
            os.write(master, b"/bin/sleep 5\n")
            time.sleep(0.10)
            os.write(master, b"\x1a")
            stopped = read_until(master, b"msh$ ")
            self.assertIn(b"Stopped", stopped)

            os.write(master, b"jobs\n")
            listing = read_until(master, b"msh$ ")
            self.assertRegex(listing, rb"\[1\] Stopped /bin/sleep 5")

            os.write(master, b"fg %1\n")
            time.sleep(0.10)
            os.write(master, b"\x03")
            self.assertIn(b"msh$ ", read_until(master, b"msh$ "))
            os.write(master, b"exit 0\n")
            read_until(master, b"marker-that-will-not-appear", timeout=1)
            waited, status = os.waitpid(child, 0)
            reaped = True
            self.assertEqual(waited, child)
            self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        except TimeoutError as error:
            if b"marker-that-will-not-appear" not in str(error).encode():
                raise
            waited, status = os.waitpid(child, 0)
            reaped = True
            self.assertEqual(waited, child)
            self.assertEqual(os.waitstatus_to_exitcode(status), 0)
        finally:
            os.close(master)
            if not reaped:
                try:
                    os.kill(child, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                os.waitpid(child, 0)


if __name__ == "__main__":
    if not Path(SHELL_BIN).is_file():
        raise SystemExit(f"reference binary does not exist: {SHELL_BIN}")
    unittest.main(verbosity=2)
