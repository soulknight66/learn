"""Public black-box examples for a Cinder implementation."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import unittest


TIMEOUT_SECONDS = 3


class CinderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        configured = os.environ.get("CINDER_BIN")
        if not configured:
            raise unittest.SkipTest("set CINDER_BIN to the interpreter executable")
        cls.binary = Path(configured).resolve()
        if not cls.binary.is_file():
            raise RuntimeError(f"CINDER_BIN is not a file: {cls.binary}")

    def run_cinder(self, source: bytes) -> subprocess.CompletedProcess[bytes]:
        argv = [str(self.binary)]
        process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(source, timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise
        return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)

    def assert_success(self, source: str, expected: str) -> None:
        result = self.run_cinder(source.encode("ascii"))
        self.assertEqual(result.returncode, 0, result.stderr.decode("ascii", "replace"))
        self.assertEqual(result.stdout, expected.encode("ascii"))
        self.assertEqual(result.stderr, b"")

    def assert_error(self, source: str) -> None:
        result = self.run_cinder(source.encode("ascii"))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertTrue(result.stderr.startswith(b"error:"), result.stderr)

    def test_empty_source(self) -> None:
        self.assert_success("", "")

    def test_arithmetic_and_signed_division(self) -> None:
        self.assert_success("7 5 + . 7 5 - . -7 3 / . -7 3 mod .", "12\n2\n-2\n-1\n")

    def test_stack_words(self) -> None:
        self.assert_success("1 2 over rot swap .s depth .", "2 1 1\n3\n")

    def test_comparison_and_bitwise_words(self) -> None:
        self.assert_success("2 3 < . 2 3 > . 6 3 xor . 0 invert .", "-1\n0\n5\n-1\n")

    def test_comments_and_hash_inside_token(self) -> None:
        self.assert_success("# discard 99\n10  # another comment\n2 * .", "20\n")
        self.assert_error("word#part")

    def test_definition_and_nested_call(self) -> None:
        self.assert_success(": sq dup * ; : fourth sq sq ; 3 fourth .", "81\n")

    def test_nested_conditionals(self) -> None:
        source = ": sign dup 0 < if drop -1 else 0 > if 1 else 0 then then ; -8 sign . 0 sign . 9 sign ."
        self.assert_success(source, "-1\n0\n1\n")

    def test_recursive_word(self) -> None:
        self.assert_success(": fact dup 1 > if dup 1 - recurse * else drop 1 then ; 6 fact .", "720\n")

    def test_emit_and_cr(self) -> None:
        self.assert_success("65 emit 66 emit cr", "AB\n")

    def test_representative_errors(self) -> None:
        for source in ("drop", "1 0 /", "missing", ": unfinished 1", "if", "9223372036854775808"):
            with self.subTest(source=source):
                self.assert_error(source)


if __name__ == "__main__":
    unittest.main()
