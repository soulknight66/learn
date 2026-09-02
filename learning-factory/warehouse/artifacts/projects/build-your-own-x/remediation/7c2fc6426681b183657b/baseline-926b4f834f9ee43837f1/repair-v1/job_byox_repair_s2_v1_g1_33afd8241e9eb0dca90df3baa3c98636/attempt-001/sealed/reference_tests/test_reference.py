"""Evaluator-owned boundary and malformed-input tests for the sealed reference."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import unittest


TIMEOUT_SECONDS = 5
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BINARY = ROOT / "sealed" / "reference" / "build" / "cinder-reference"


class ReferenceBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binary = Path(os.environ.get("REFERENCE_BIN", DEFAULT_BINARY)).resolve()
        if not cls.binary.is_file():
            raise RuntimeError(f"build the reference executable first: {cls.binary}")

    def run_source(self, source: bytes, timeout: int = TIMEOUT_SECONDS) -> subprocess.CompletedProcess[bytes]:
        argv = [str(self.binary)]
        process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(source, timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise
        return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)

    def assert_ok(self, source: bytes, output: bytes = b"") -> None:
        result = self.run_source(source)
        self.assertEqual(result.returncode, 0, result.stderr.decode("ascii", "replace"))
        self.assertEqual(result.stdout, output)
        self.assertEqual(result.stderr, b"")

    def assert_fails(self, source: bytes, phrase: bytes | None = None) -> None:
        result = self.run_source(source)
        self.assertEqual(result.returncode, 2, result)
        self.assertTrue(result.stderr.startswith(b"error:"), result.stderr)
        if phrase is not None:
            self.assertIn(phrase, result.stderr)

    def test_signed_integer_boundaries_and_formatting(self) -> None:
        self.assert_ok(
            b"-9223372036854775808 . 9223372036854775807 .",
            b"-9223372036854775808\n9223372036854775807\n",
        )
        self.assert_fails(b"9223372036854775808", b"integer")
        self.assert_fails(b"-9223372036854775809", b"integer")

    def test_wrapping_arithmetic(self) -> None:
        self.assert_ok(
            b"9223372036854775807 1 + . -9223372036854775808 1 - .",
            b"-9223372036854775808\n9223372036854775807\n",
        )

    def test_all_division_sign_combinations(self) -> None:
        self.assert_ok(
            b"7 3 / . 7 -3 / . -7 3 / . -7 -3 / . "
            b"7 3 mod . 7 -3 mod . -7 3 mod . -7 -3 mod .",
            b"2\n-2\n-2\n2\n1\n1\n-1\n-1\n",
        )
        self.assert_fails(b"-9223372036854775808 -1 /", b"overflow")

    def test_empty_stack_display_is_one_newline(self) -> None:
        self.assert_ok(b".s", b"\n")

    def test_exact_input_limit_and_one_byte_too_many(self) -> None:
        self.assert_ok(b" " * 65536)
        self.assert_fails(b" " * 65537, b"65536")

    def test_data_stack_capacity(self) -> None:
        exact = (b"0 " * 256) + (b"drop " * 256)
        self.assert_ok(exact)
        self.assert_fails(b"0 " * 257, b"stack overflow")

    def test_user_dictionary_capacity(self) -> None:
        definitions = b" ".join(f": w{i} ;".encode("ascii") for i in range(64))
        self.assert_ok(definitions + b" w63")
        self.assert_fails(definitions + b" : excess ;", b"dictionary")

    def test_word_name_length_and_duplicate_rules(self) -> None:
        name31 = b"a" * 31
        self.assert_ok(b": " + name31 + b" 42 ; " + name31 + b" .", b"42\n")
        for source in (
            b": " + (b"a" * 32) + b" ;",
            b": dup ;",
            b": if ;",
            b": 12 ;",
            b": 9223372036854775808 7 ;",
            b": same ; : same ;",
        ):
            with self.subTest(source=source[:48]):
                self.assert_fails(source, b"definition")

    def test_code_arena_exact_capacity(self) -> None:
        exact_body = b"0 " * 4095 + b"drop "
        self.assert_ok(b": full " + exact_body + b";")
        self.assert_fails(b": full " + exact_body + b"; : no-room ;", b"code arena")

    def test_patch_stack_capacity_and_malformed_nesting(self) -> None:
        nested64 = (b"1 if " * 64) + (b"then " * 64)
        self.assert_ok(b": nested " + nested64 + b";")
        self.assert_fails(b": nested " + (b"1 if " * 65), b"nesting")
        for source in (b": x else ;", b": x then ;", b": x 1 if else else then ;", b": x 1 if ;"):
            with self.subTest(source=source):
                self.assert_fails(source, b"control flow")

    def test_recursion_limit_and_safe_unwind(self) -> None:
        definition = b": down dup 0 > if 1 - recurse else drop then ; "
        self.assert_ok(definition + b"256 down depth .", b"0\n")
        self.assert_fails(definition + b"257 down", b"return stack")

    def test_compile_only_and_unfinished_constructs(self) -> None:
        for source in (b";", b"if", b"else", b"then", b"recurse", b":", b": x", b": x 1 if"):
            with self.subTest(source=source):
                self.assert_fails(source)

    def test_comments_at_eof_and_token_boundary(self) -> None:
        self.assert_ok(b"4 5 + . # no final newline", b"9\n")
        self.assert_fails(b"4#5")


if __name__ == "__main__":
    unittest.main()
