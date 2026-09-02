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

    def test_large_integer_avoids_python_decimal_limit(self):
        digits = "9" * 5000
        result = self.run_cli("-e", digits)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, digits + "\n")
        self.assertEqual(result.stderr, "")

    def test_reader_resource_boundaries_are_controlled(self):
        for source, message in (
            ("8" * 10001, "integer exceeds 10000 digits"),
            ("(" * 257 + "0" + ")" * 257, "maximum nesting depth 256"),
        ):
            with self.subTest(message=message):
                result = self.run_cli("-e", source)
                self.assertEqual(result.returncode, 2)
                self.assertIn("error: " + message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_non_tail_stack_exhaustion_is_controlled(self):
        source = """
        (def non-tail
          (fn (n)
            (if (= n 0) 0 (+ 1 (non-tail (- n 1))))))
        (non-tail 2000)
        """
        result = self.run_cli("-e", source)
        self.assertEqual(result.returncode, 2)
        self.assertIn("error: evaluation exceeded the host recursion budget", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
