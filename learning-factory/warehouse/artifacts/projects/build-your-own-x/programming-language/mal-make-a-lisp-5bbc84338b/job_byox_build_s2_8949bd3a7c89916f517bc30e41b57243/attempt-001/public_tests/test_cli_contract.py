import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CliContractTests(unittest.TestCase):
    def run_cli(self, *args, input_text=None):
        return subprocess.run(
            [sys.executable, "-m", "pebble.cli", *args],
            cwd=Path(__file__).resolve().parents[1],
            env=os.environ.copy(),
            input=input_text,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )

    def test_expression_mode_prints_final_value(self):
        result = self.run_cli("-e", "(+ 20 22)")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "42\n")
        self.assertEqual(result.stderr, "")

    def test_file_mode_only_emits_explicit_prints(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "program.pebble"
            path.write_text('(print "visible")\n(+ 1 2)\n', encoding="utf-8")
            result = self.run_cli(str(path))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '"visible"\n')
        self.assertEqual(result.stderr, "")

    def test_language_failure_has_no_traceback(self):
        result = self.run_cli("-e", "unknown-name")
        self.assertEqual(result.returncode, 2)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
