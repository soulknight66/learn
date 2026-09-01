#!/usr/bin/env python3
"""Learner-visible black-box tests for the msh behavioral contract."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


SHELL_PATH = None


def run_shell(script, command_mode=False):
    argv = [str(SHELL_PATH)]
    if command_mode:
        argv += ["-c", script]
        input_text = None
    else:
        input_text = script
    return subprocess.run(
        argv,
        input=input_text,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=3.0,
        check=False,
    )


class InvocationTests(unittest.TestCase):
    def test_empty_batch_input_is_quiet(self):
        result = run_shell("")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("msh$", result.stderr)

    def test_bad_cli_usage_returns_two(self):
        result = subprocess.run(
            [str(SHELL_PATH), "unexpected"],
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3.0,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr)


class ParsingTests(unittest.TestCase):
    def test_quotes_escapes_and_empty_argument(self):
        result = run_shell("printf '[%s]\\n' \"two words\" 'three four' a\\ b \"\"", command_mode=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "[two words]\n[three four]\n[a b]\n[]\n")

    def test_quoted_metacharacters_are_literal(self):
        result = run_shell("printf '%s\\n' '|' '&' '$HOME' '*' ';'", command_mode=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "|\n&\n$HOME\n*\n;\n")

    def test_syntax_error_does_not_abort_stream(self):
        result = run_shell("printf before\nprintf 'unterminated\nprintf after\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "beforeafter")
        self.assertIn("msh:", result.stderr)


class ExecutionTests(unittest.TestCase):
    def test_simple_external_command(self):
        result = run_shell("printf hello", command_mode=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "hello")

    def test_adjacent_pipeline_operators(self):
        result = run_shell("printf abc|tr a-z A-Z", command_mode=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "ABC")

    def test_pipeline_uses_last_status(self):
        self.assertEqual(run_shell("false | true", command_mode=True).returncode, 0)
        self.assertEqual(run_shell("true | false", command_mode=True).returncode, 1)

    def test_command_not_found_is_127(self):
        result = run_shell("msh_public_test_command_that_does_not_exist", command_mode=True)
        self.assertEqual(result.returncode, 127)
        self.assertIn("msh:", result.stderr)

    def test_large_pipeline_does_not_serialize(self):
        result = run_shell("seq 1 20000 | wc -l", command_mode=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "20000")


class BuiltinsTests(unittest.TestCase):
    def test_cd_changes_parent_directory(self):
        with tempfile.TemporaryDirectory(prefix="msh-public-") as directory:
            result = run_shell(f"cd {directory}\npwd\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), Path(directory))

    def test_exit_status_and_invalid_exit_recovery(self):
        result = run_shell("exit not-a-number\nprintf alive\nexit 7\n")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout, "alive")
        self.assertIn("msh:", result.stderr)

    def test_builtin_in_pipeline_is_rejected(self):
        result = run_shell("cd / | cat", command_mode=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("msh:", result.stderr)


class JobsTests(unittest.TestCase):
    def test_background_job_is_listed_and_waitable(self):
        result = run_shell("sleep 0.05 &\njobs\nwait\nprintf done\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, re.compile(r"\[1\] (Running|Done) [0-9]+ sleep 0\.05"))
        self.assertTrue(result.stdout.endswith("done"), result.stdout)

    def test_background_marker_does_not_block_launch(self):
        result = run_shell("sleep 0.15 &\nprintf foreground\nwait\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("foreground", result.stdout)
        self.assertRegex(result.stdout, re.compile(r"\[1\] [0-9]+"))


def main():
    global SHELL_PATH

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--shell", required=True)
    parser.add_argument(
        "--stage",
        choices=("all", "invocation", "parsing", "execution", "builtins", "jobs"),
        default="all",
    )
    known, remaining = parser.parse_known_args()
    SHELL_PATH = Path(known.shell).resolve()
    if not SHELL_PATH.is_file():
        parser.error(f"shell executable not found: {SHELL_PATH}")
    if known.stage == "all":
        unittest.main(argv=[os.path.basename(__file__)] + remaining)
        return

    stages = {
        "invocation": InvocationTests,
        "parsing": ParsingTests,
        "execution": ExecutionTests,
        "builtins": BuiltinsTests,
        "jobs": JobsTests,
    }
    verbosity = 2 if "-v" in remaining or "--verbose" in remaining else 1
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(stages[known.stage])
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
