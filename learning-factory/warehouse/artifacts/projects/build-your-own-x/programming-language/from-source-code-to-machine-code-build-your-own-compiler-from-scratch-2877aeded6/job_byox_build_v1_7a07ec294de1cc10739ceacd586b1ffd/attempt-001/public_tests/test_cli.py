import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def command(self, *arguments):
        environment = os.environ.copy()
        # Honor the implementation selected by the outer test command; fall back to the starter.
        environment["PYTHONPATH"] = os.environ.get("PYTHONPATH", str(ROOT / "starter"))
        return subprocess.run(
            [sys.executable, "-m", "minnow", *arguments],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )

    def test_compile_then_run(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "countdown.mbc"
            compiled = self.command("compile", str(ROOT / "public_tests/fixtures/countdown.mno"), str(output_path))
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = self.command("run", "--max-steps", "1000", str(output_path))
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, "3\n2\n1\n")

    def test_source_error_has_no_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "bad.mno"
            source_path.write_text("print @;", encoding="utf-8")
            result = self.command("exec", str(source_path))
            self.assertEqual(result.returncode, 2)
            self.assertIn("LEX", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
