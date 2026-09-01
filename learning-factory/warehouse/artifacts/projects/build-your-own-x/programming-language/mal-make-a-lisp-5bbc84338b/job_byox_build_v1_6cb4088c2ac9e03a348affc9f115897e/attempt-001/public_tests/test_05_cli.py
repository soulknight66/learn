import os
import io
import subprocess
import sys
import tempfile
import unittest


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-m", "sprig"] + list(arguments),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

    def test_expression_mode_shares_environment(self):
        result = self.run_cli("-e", "(def x 40) (+ x 2)")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "40\n42\n")

    def test_vm_mode_and_disassembly(self):
        result = self.run_cli("--engine", "vm", "--disassemble", "-e", "(+ 2 3)")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CALL 2", result.stdout)
        self.assertTrue(result.stdout.endswith("5\n"))

    def test_language_error_has_no_traceback(self):
        result = self.run_cli("-e", "(+ 1 true)")
        self.assertEqual(result.returncode, 2)
        self.assertIn("BUILTIN_TYPE", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_file_mode_reads_utf8(self):
        descriptor, path = tempfile.mkstemp(prefix="sprig-public-", suffix=".sp")
        try:
            os.close(descriptor)
            with io.open(path, "w", encoding="utf-8") as handle:
                handle.write('(type "snowman: ☃")')
            result = self.run_cli(path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "string\n")
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
