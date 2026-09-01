from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "sealed" / "reference"
EXECUTABLE = TARGET / "stackvm"


class ReferenceBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            ["make", "-C", str(TARGET), "clean", "all"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "reference build failed\n"
                + result.stdout.decode(errors="replace")
                + result.stderr.decode(errors="replace")
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
        result = self.run_vm(source)
        self.assertEqual(result.returncode, status)
        self.assertEqual(result.stdout, stdout)
        self.assertEqual(result.stderr, stderr)

    def test_literal_extrema_and_leading_zeroes(self):
        self.assert_run(
            "-9223372036854775808 . 9223372036854775807 . -0 . 00012 .",
            stdout=b"-9223372036854775808\n9223372036854775807\n0\n12\n",
        )

    def test_out_of_range_and_malformed_literals(self):
        bad_tokens = [
            "9223372036854775808",
            "-9223372036854775809",
            "+1",
            "1x",
            "--1",
            "DUP",
        ]
        for token in bad_tokens:
            with self.subTest(token=token):
                self.assert_run(token, status=2, stderr=b"compile error\n")

    def test_arithmetic_overflow_paths(self):
        programs = [
            "9223372036854775807 1 +",
            "-9223372036854775808 1 -",
            "9223372036854775807 2 *",
            "-9223372036854775808 -1 /",
        ]
        for source in programs:
            with self.subTest(source=source):
                self.assert_run(
                    source,
                    status=7,
                    stderr=b"arithmetic overflow\n",
                )

    def test_division_truncates_toward_zero(self):
        self.assert_run(
            "7 3 / . -7 3 / . 7 -3 / . -7 -3 / .",
            stdout=b"2\n-2\n-2\n2\n",
        )

    def test_each_stack_word_checks_underflow(self):
        for source in ["dup", "drop", "swap", "over", "=", ".", "1 +", "1 /"]:
            with self.subTest(source=source):
                self.assert_run(
                    source,
                    status=3,
                    stderr=b"stack underflow\n",
                )

    def test_stack_capacity_boundaries(self):
        self.assert_run("0 " * 256)
        self.assert_run(
            "0 " * 257,
            status=4,
            stderr=b"stack overflow\n",
        )
        self.assert_run(
            "0 " * 256 + "dup",
            status=4,
            stderr=b"stack overflow\n",
        )
        self.assert_run(
            "0 " * 256 + "over",
            status=4,
            stderr=b"stack overflow\n",
        )

    def test_compile_errors_prevent_all_execution(self):
        self.assert_run(
            "10 . 20 . not-a-word",
            status=2,
            stderr=b"compile error\n",
        )

    def test_runtime_errors_preserve_prior_output(self):
        self.assert_run(
            "10 . drop",
            status=3,
            stdout=b"10\n",
            stderr=b"stack underflow\n",
        )

    def test_input_limit(self):
        accepted = b"1 ." + b" " * (4095 - 3)
        self.assertEqual(len(accepted), 4095)
        self.assert_run(accepted, stdout=b"1\n")
        self.assert_run(
            b" " * 4096,
            status=6,
            stderr=b"input too large\n",
        )
        self.assert_run(
            b"x" * 5000,
            status=6,
            stderr=b"input too large\n",
        )

    def test_all_control_bytes_are_separators(self):
        source = b"2" + bytes(range(0x21)) + b"3 + ."
        self.assert_run(source, stdout=b"5\n")

    def test_input_can_arrive_in_short_reads(self):
        process = subprocess.Popen(
            [str(EXECUTABLE)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for chunk in [b"12", b" ", b"3", b" +", b" ."]:
            process.stdin.write(chunk)
            process.stdin.flush()
        process.stdin.close()
        process.stdin = None
        stdout, stderr = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(stdout, b"15\n")
        self.assertEqual(stderr, b"")


if __name__ == "__main__":
    unittest.main()

