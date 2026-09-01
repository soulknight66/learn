from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

import learnfactory.strict_json as strict_json_module
from learnfactory.strict_json import StrictJsonError, strict_json_loads


class StrictJsonTests(unittest.TestCase):
    def test_rejects_unpaired_surrogates_recursively_in_keys_and_values(self) -> None:
        documents = (
            '"\\ud800"',
            '{"key":[{"nested":"\\udfff"}]}',
            '{"\\ud800":true}',
            '[["ok"],{"deep":{"\\udfff":0}}]',
        )
        for document in documents:
            with self.subTest(document=document):
                with self.assertRaisesRegex(StrictJsonError, "unpaired surrogate"):
                    strict_json_loads(document)

    def test_accepts_valid_unicode_and_paired_surrogate_escapes(self) -> None:
        self.assertEqual(
            {"雪": ["😀", "café"]},
            strict_json_loads('{"雪":["\\ud83d\\ude00","café"]}'),
        )

    def test_resource_limits_do_not_depend_on_interpreter_globals(self) -> None:
        original_recursion_limit = sys.getrecursionlimit()
        original_integer_limit = (
            sys.get_int_max_str_digits()
            if hasattr(sys, "get_int_max_str_digits")
            else None
        )
        try:
            sys.setrecursionlimit(10_000)
            if hasattr(sys, "set_int_max_str_digits"):
                sys.set_int_max_str_digits(0)
            documents = (
                "9" * (strict_json_module.MAX_JSON_INTEGER_DIGITS + 1),
                "[" * (strict_json_module.MAX_JSON_NESTING_DEPTH + 1)
                + "0"
                + "]" * (strict_json_module.MAX_JSON_NESTING_DEPTH + 1),
                "0."
                + "0" * strict_json_module.MAX_JSON_NUMBER_CHARACTERS
                + "1",
            )
            for document in documents:
                with self.subTest(length=len(document)):
                    with self.assertRaises(StrictJsonError):
                        strict_json_loads(document)
        finally:
            sys.setrecursionlimit(original_recursion_limit)
            if (
                original_integer_limit is not None
                and hasattr(sys, "set_int_max_str_digits")
            ):
                sys.set_int_max_str_digits(original_integer_limit)

    def test_integer_limit_is_sign_aware(self) -> None:
        digits = "9" * strict_json_module.MAX_JSON_INTEGER_DIGITS
        self.assertEqual(int(digits), strict_json_loads(digits))
        self.assertEqual(-int(digits), strict_json_loads("-" + digits))
        with self.assertRaisesRegex(StrictJsonError, "digit limit"):
            strict_json_loads("9" * (len(digits) + 1))

    def test_structural_string_and_token_limits_are_explicit(self) -> None:
        with patch.object(strict_json_module, "MAX_JSON_NODES", 5):
            with self.assertRaisesRegex(StrictJsonError, "node limit"):
                strict_json_loads("[0,0,0,0,0]")
        with patch.object(strict_json_module, "MAX_JSON_TOKENS", 5):
            with self.assertRaisesRegex(StrictJsonError, "token limit"):
                strict_json_loads("[0,0,0]")
        with patch.object(strict_json_module, "MAX_JSON_STRING_CHARACTERS", 4):
            with self.assertRaisesRegex(StrictJsonError, "string token"):
                strict_json_loads('"12345"')

    def test_numeric_preflight_rejects_before_regex_sees_an_overlong_token(self) -> None:
        class RecordingNumberPattern:
            called = False

            def fullmatch(self, value: str) -> object:
                self.called = True
                raise AssertionError(f"unexpected regex input of {len(value)} characters")

        recorder = RecordingNumberPattern()
        document = "1" * (strict_json_module.MAX_JSON_NUMBER_CHARACTERS + 10_000)
        with patch.object(strict_json_module, "_NUMBER_RE", recorder):
            with self.assertRaisesRegex(StrictJsonError, "number literal"):
                strict_json_loads(document)
        self.assertFalse(recorder.called)

    def test_only_exact_immutable_builtin_inputs_are_admitted(self) -> None:
        class LyingBytearray(bytearray):
            def __len__(self) -> int:
                return 1

        class LyingString(str):
            def encode(self, *args: object, **kwargs: object) -> bytes:
                return b""

        payload = "[" + "0," * 10_000 + "0]"
        values = (
            bytearray(payload.encode("utf-8")),
            LyingBytearray(payload.encode("utf-8")),
            LyingString(payload),
        )
        for value in values:
            with self.subTest(input_type=type(value).__name__):
                with self.assertRaisesRegex(StrictJsonError, "text or bytes"):
                    strict_json_loads(value, max_bytes=10)  # type: ignore[arg-type]

    def test_exact_string_character_lower_bound_precedes_utf8_count(self) -> None:
        with self.assertRaisesRegex(StrictJsonError, "byte limit"):
            strict_json_loads("0" * 1_000_000, max_bytes=10)


if __name__ == "__main__":
    unittest.main()
