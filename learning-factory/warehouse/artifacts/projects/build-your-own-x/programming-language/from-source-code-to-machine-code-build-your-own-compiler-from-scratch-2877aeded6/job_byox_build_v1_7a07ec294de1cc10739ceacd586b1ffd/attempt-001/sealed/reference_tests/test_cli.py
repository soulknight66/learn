import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CliTests(unittest.TestCase):
    def command(self, *arguments):
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "sealed/reference")
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
            source = Path(directory) / "sum.mno"
            bytecode = Path(directory) / "sum.mbc"
            source.write_text("let x = 2; print x * 5;", encoding="utf-8")
            compiled = self.command("compile", str(source), str(bytecode))
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertEqual(compiled.stdout, "")
            executed = self.command("run", "--max-steps", "20", str(bytecode))
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, "10\n")

    def test_compile_error_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.mno"
            bytecode = Path(directory) / "keep.mbc"
            source.write_text("print @;", encoding="utf-8")
            bytecode.write_bytes(b"original")
            result = self.command("compile", str(source), str(bytecode))
            self.assertEqual(result.returncode, 2)
            self.assertIn("LEX", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(bytecode.read_bytes(), b"original")
            self.assertEqual(list(Path(directory).glob(".keep.mbc.*")), [])

    def test_invalid_utf8_is_reported_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "invalid.mno"
            source.write_bytes(b"print \xff;")
            result = self.command("exec", str(source))
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)
            self.assertNotEqual(result.stderr, "")

    def test_nonpositive_cli_limit_is_usage_error(self):
        result = self.command("run", "--max-steps", "0", "missing.mbc")
        self.assertEqual(result.returncode, 2)
        self.assertIn("positive integer", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
