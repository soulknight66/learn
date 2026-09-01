#!/usr/bin/env python3
"""Sealed black-box tests that do not require a controlling terminal."""

import argparse
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import unittest


SHELL_PATH = None
PG_PROBE = None


def run_shell(script, command_mode=False, env=None, timeout=4.0):
    argv = [str(SHELL_PATH)]
    input_text = script
    if command_mode:
        argv.extend(["-c", script])
        input_text = None
    return subprocess.run(
        argv,
        input=input_text,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
        env=env,
    )


class SyntaxAndStatusTests(unittest.TestCase):
    def test_each_malformed_line_returns_two(self):
        malformed = ["| true", "true |", "true || false", "&", "true & false",
                     "true &&", "'open", '"open', "word\\"]
        for line in malformed:
            result = run_shell(line, command_mode=True)
            self.assertEqual(result.returncode, 2, (line, result.stderr))
            self.assertEqual(result.stdout, "", line)
            self.assertIn("msh:", result.stderr, line)

    def test_permission_denied_is_126(self):
        with tempfile.TemporaryDirectory(prefix="msh-sealed-") as directory:
            target = Path(directory) / "not-executable"
            target.write_text("plain data\n")
            target.chmod(stat.S_IRUSR | stat.S_IWUSR)
            result = run_shell(str(target), command_mode=True)
        self.assertEqual(result.returncode, 126, result.stderr)

    def test_signal_status_is_normalized(self):
        result = run_shell("sh -c 'kill -TERM $$'", command_mode=True)
        self.assertEqual(result.returncode, 128 + 15, result.stderr)

    def test_exit_without_operand_uses_previous_status(self):
        result = run_shell("false\nexit\n")
        self.assertEqual(result.returncode, 1, result.stderr)

    def test_non_goal_metacharacters_remain_words(self):
        result = run_shell("printf '%s\\n' '<' '>' '$x' '*.c' ';'", command_mode=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "<\n>\n$x\n*.c\n;\n")


class ProcessTests(unittest.TestCase):
    def test_deep_large_pipeline_reaches_eof(self):
        command = "seq 1 40000" + " | cat" * 8 + " | wc -l"
        result = run_shell(command, command_mode=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "40000")

    def test_pipeline_members_share_first_child_group(self):
        command = "{} first | {} second".format(PG_PROBE, PG_PROBE)
        result = run_shell(command, command_mode=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        matches = re.findall(r"PG_PROBE (first|second) ([0-9]+) ([0-9]+)", result.stderr)
        self.assertEqual(len(matches), 2, result.stderr)
        records = {label: (int(pid), int(group)) for label, pid, group in matches}
        self.assertEqual(records["first"][0], records["first"][1])
        self.assertEqual(records["first"][1], records["second"][1])

    def test_distinct_pipelines_get_monotonic_jobs(self):
        result = run_shell("sleep 0.02 &\nsleep 0.03 &\njobs\nwait\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"\[1\] [0-9]+")
        self.assertRegex(result.stdout, r"\[2\] [0-9]+")
        self.assertRegex(result.stdout, r"\[1\] (Running|Done) [0-9]+ sleep 0\.02")
        self.assertRegex(result.stdout, r"\[2\] (Running|Done) [0-9]+ sleep 0\.03")


class BuiltinTests(unittest.TestCase):
    def test_cd_without_operand_uses_home(self):
        with tempfile.TemporaryDirectory(prefix="msh-home-") as directory:
            environment = os.environ.copy()
            environment["HOME"] = directory
            result = run_shell("cd\npwd\n", env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), Path(directory))

    def test_missing_home_is_diagnostic_and_recoverable(self):
        environment = os.environ.copy()
        environment.pop("HOME", None)
        result = run_shell("cd\nprintf survived\n", env=environment)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "survived")
        self.assertIn("HOME", result.stderr)

    def test_builtin_with_background_is_rejected_before_launch(self):
        result = run_shell("exit 9 &\nprintf survived\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "survived")
        self.assertIn("msh:", result.stderr)


def main():
    global SHELL_PATH, PG_PROBE

    parser = argparse.ArgumentParser()
    parser.add_argument("--shell", required=True)
    parser.add_argument("--pg-probe", required=True)
    known, remaining = parser.parse_known_args()
    SHELL_PATH = Path(known.shell).resolve()
    PG_PROBE = Path(known.pg_probe).resolve()
    unittest.main(argv=[os.path.basename(__file__)] + remaining)


if __name__ == "__main__":
    main()
