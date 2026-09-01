#!/usr/bin/env python3
"""Bounded stress cases for parser growth, pipeline depth, and job retention."""

import argparse
import os
from pathlib import Path
import re
import subprocess
import unittest


SHELL_PATH = None


def run_shell(script, timeout=8.0):
    return subprocess.run(
        [str(SHELL_PATH)],
        input=script,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


class AdversarialTests(unittest.TestCase):
    def test_sixty_four_kibibyte_word_survives_parser_growth(self):
        payload = "z" * 65536
        result = run_shell("printf '%s' '" + payload + "' | wc -c\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(len(payload)))

    def test_thirty_two_consumers_observe_eof(self):
        command = "printf x" + " | cat" * 32 + "\n"
        result = run_shell(command)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "x")

    def test_two_hundred_syntax_errors_recover(self):
        result = run_shell("|\n" * 200 + "printf recovered\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "recovered")
        self.assertEqual(result.stderr.count("msh:"), 200)

    def test_twenty_five_background_jobs_get_unique_ids(self):
        result = run_shell("true &\n" * 25 + "wait\nprintf complete\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        launches = re.findall(r"^\[([0-9]+)\] [0-9]+$", result.stdout,
                              flags=re.MULTILINE)
        self.assertEqual([int(value) for value in launches], list(range(1, 26)))
        self.assertTrue(result.stdout.endswith("complete"), result.stdout)


def main():
    global SHELL_PATH

    parser = argparse.ArgumentParser()
    parser.add_argument("--shell", required=True)
    known, remaining = parser.parse_known_args()
    SHELL_PATH = Path(known.shell).resolve()
    unittest.main(argv=[os.path.basename(__file__)] + remaining)


if __name__ == "__main__":
    main()
