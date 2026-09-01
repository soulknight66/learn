"""Permanent deterministic tests for the learner-visible shell envelope."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
STARTER = REPOSITORY_ROOT / "starter"
API_SMOKE = Path(__file__).with_name("api_smoke.c")


class PermanentPublicContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temporary = tempfile.TemporaryDirectory(prefix="minish-public-")
        cls.work = Path(cls._temporary.name) / "starter"
        shutil.copytree(STARTER, cls.work)
        cls._run([
            "make", "clean", "all",
            "CFLAGS=-std=c11 -Wall -Wextra -Wpedantic -Werror -g",
        ], cwd=cls.work)

    @classmethod
    def tearDownClass(cls):
        cls._temporary.cleanup()

    @staticmethod
    def _run(argv, cwd, input_text=None, check=True):
        environment = os.environ.copy()
        environment["LC_ALL"] = "C"
        return subprocess.run(
            argv,
            cwd=cwd,
            input=input_text,
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=check,
            env=environment,
        )

    def test_expected_stage_files_are_present(self):
        expected = {
            "Makefile",
            "README.md",
            "include/shell.h",
            "include/lexer.h",
            "include/parser.h",
            "include/executor.h",
            "src/main.c",
            "src/shell.c",
            "src/lexer.c",
            "src/parser.c",
            "src/executor.c",
        }
        self.assertTrue(expected.issubset({
            path.relative_to(STARTER).as_posix()
            for path in STARTER.rglob("*")
            if path.is_file()
        }))

    def test_help_describes_both_modes(self):
        result = self._run(["./minish", "--help"], cwd=self.work)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("-c COMMAND", result.stdout)
        self.assertIn("standard input", result.stdout)
        self.assertEqual("", result.stderr)

    def test_empty_commands_succeed_quietly(self):
        for command in ("", "  \t\n"):
            with self.subTest(command=repr(command)):
                result = self._run(["./minish", "-c", command], cwd=self.work)
                self.assertEqual("", result.stdout)
                self.assertEqual("", result.stderr)

    def test_multiple_empty_physical_lines_succeed_quietly(self):
        result = self._run(["./minish", "-c", "   \n\t\n"], cwd=self.work)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_noninteractive_eof_is_quiet(self):
        result = self._run(["./minish"], cwd=self.work, input_text="")
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_embedded_nul_is_rejected_without_executing_prefix(self):
        result = self._run(
            ["./minish"], cwd=self.work, input_text="ignored\x00tail\n",
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("NUL byte", result.stderr)

    def test_unknown_option_is_a_usage_error(self):
        result = self._run(
            ["./minish", "--unknown"], cwd=self.work, check=False
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("Usage:", result.stderr)

    def test_missing_command_operand_is_a_usage_error(self):
        result = self._run(["./minish", "-c"], cwd=self.work, check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn("Usage:", result.stderr)

    def test_public_headers_link_as_a_library(self):
        probe = Path(self._temporary.name) / "api_smoke"
        self._run(
            [
                os.environ.get("CC", "cc"),
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Wpedantic",
                "-Werror",
                "-I",
                str(self.work / "include"),
                str(API_SMOKE),
                str(self.work / "libminish.a"),
                "-o",
                str(probe),
            ],
            cwd=self.work,
        )
        self._run([str(probe)], cwd=self.work)


if __name__ == "__main__":
    unittest.main()
