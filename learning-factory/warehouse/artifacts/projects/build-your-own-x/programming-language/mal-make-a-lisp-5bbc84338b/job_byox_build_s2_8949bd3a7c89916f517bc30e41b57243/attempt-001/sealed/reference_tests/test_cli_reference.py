import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CliReferenceTests(unittest.TestCase):
    def run_cli(self, *arguments, input_text=None):
        return subprocess.run(
            [sys.executable, "-m", "pebble.cli", *arguments],
            cwd=ROOT,
            env=os.environ.copy(),
            input=input_text,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )

    def test_interactive_mode_retains_globals(self):
        result = self.run_cli(input_text="(def x 4)\n(+ x 3)\n")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, "pebble> 4\npebble> 7\npebble> ")

    def test_missing_file_is_controlled_error(self):
        result = self.run_cli("this-file-does-not-exist.pebble")
        self.assertEqual(result.returncode, 2)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_expression_and_file_are_mutually_exclusive(self):
        result = self.run_cli("-e", "1", "program.pebble")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mutually exclusive", result.stderr)


if __name__ == "__main__":
    unittest.main()
