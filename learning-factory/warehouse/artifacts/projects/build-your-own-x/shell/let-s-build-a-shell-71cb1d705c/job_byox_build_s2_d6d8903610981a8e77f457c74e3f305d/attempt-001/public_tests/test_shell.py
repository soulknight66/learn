#!/usr/bin/env python3
"""Public, implementation-agnostic contract checks for msh."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SHELL_BIN = os.environ.get("MSH_BIN", "starter/msh")


def run_command(source, *, input_text=None, cwd=None, timeout=3):
    argv = [SHELL_BIN, "-c", source] if input_text is None else [SHELL_BIN]
    return subprocess.run(
        argv,
        input=input_text,
        text=True,
        capture_output=True,
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


if __name__ == "__main__":
    if not Path(SHELL_BIN).exists():
        raise SystemExit(f"MSH_BIN does not exist: {SHELL_BIN}")
    unittest.main(verbosity=2)
