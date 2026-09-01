import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
TARGET = Path(os.environ.get("STACKVM_TARGET", ROOT / "starter")).resolve()
EXECUTABLE = TARGET / "stackvm"


class StackVMContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        built = subprocess.run(
            ["make", "-C", str(TARGET), "clean", "all"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )
        if built.returncode != 0:
            raise RuntimeError(
                "build failed\nstdout:\n"
                + built.stdout.decode(errors="replace")
                + "\nstderr:\n"
                + built.stderr.decode(errors="replace")
            )

    def run_vm(self, source):
        if isinstance(source, str):
            source = source.encode("ascii")
        return subprocess.run(
            [str(EXECUTABLE)],
            input=source,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3,
            check=False,
        )

    def assert_run(self, source, status=0, stdout=b"", stderr=b""):
        completed = self.run_vm(source)
        self.assertEqual(completed.returncode, status)
        self.assertEqual(completed.stdout, stdout)
        self.assertEqual(completed.stderr, stderr)

    def test_empty_and_separator_only_programs(self):
        self.assert_run(b"")
        self.assert_run(b" \t\r\n\x00\x1f")

    def test_signed_literals_and_canonical_output(self):
        self.assert_run(
            "-7 . 0 . 42 . -9223372036854775808 . 9223372036854775807 .",
            stdout=(
                b"-7\n0\n42\n-9223372036854775808\n"
                b"9223372036854775807\n"
            ),
        )

    def test_checked_arithmetic_and_division_rounding(self):
        self.assert_run(
            "2 3 + . 10 4 - . -7 6 * . 20 3 / . -20 3 / .",
            stdout=b"5\n6\n-42\n6\n-6\n",
        )

    def test_stack_words(self):
        self.assert_run(
            "7 dup + . 1 2 swap . . 3 4 over . . . 1 9 drop .",
            stdout=b"14\n1\n2\n3\n4\n3\n1\n",
        )

    def test_equality_uses_one_and_zero(self):
        self.assert_run("4 4 = . 4 5 = .", stdout=b"1\n0\n")

    def test_unknown_token_is_atomic_compile_error(self):
        self.assert_run("1 . unknown", status=2, stderr=b"compile error\n")

    def test_underflow(self):
        self.assert_run("+", status=3, stderr=b"stack underflow\n")

    def test_division_by_zero(self):
        self.assert_run("8 0 /", status=5, stderr=b"division by zero\n")

    def test_arithmetic_overflow(self):
        self.assert_run(
            "9223372036854775807 1 +",
            status=7,
            stderr=b"arithmetic overflow\n",
        )

    def test_stack_capacity(self):
        self.assert_run("1 " * 257, status=4, stderr=b"stack overflow\n")


if __name__ == "__main__":
    unittest.main()

