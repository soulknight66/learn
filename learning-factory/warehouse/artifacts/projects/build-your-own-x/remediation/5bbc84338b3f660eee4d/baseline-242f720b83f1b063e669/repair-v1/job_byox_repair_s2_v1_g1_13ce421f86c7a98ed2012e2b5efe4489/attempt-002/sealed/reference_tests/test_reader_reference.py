import sys
import unittest

from pebble import ReaderError, Symbol, format_value, read_all, read_one, tokenize


class TokenizerReferenceTests(unittest.TestCase):
    def test_token_positions_are_one_based_starts(self):
        tokens = tokenize("\n  (alpha\n   \"x\")")
        self.assertEqual(
            [(token.kind, token.line, token.column) for token in tokens],
            [
                ("LPAREN", 2, 3),
                ("ATOM", 2, 4),
                ("STRING", 3, 4),
                ("RPAREN", 3, 7),
            ],
        )

    def test_comment_does_not_consume_newline_position(self):
        tokens = tokenize("1; ignored\n2")
        self.assertEqual([(token.text, token.line, token.column) for token in tokens], [("1", 1, 1), ("2", 2, 1)])

    def test_each_permitted_escape_is_decoded(self):
        self.assertEqual(read_one(r'"\\\"\n\r\t"'), '\\"\n\r\t')

    def test_raw_carriage_return_in_string_is_rejected(self):
        with self.assertRaisesRegex(ReaderError, r"raw newline.*1:3"):
            read_one('"x\ry"')

    def test_unknown_escape_reports_escape_start(self):
        with self.assertRaisesRegex(ReaderError, r"unknown escape.*1:3"):
            read_one(r'"x\qy"')


class ReaderReferenceTests(unittest.TestCase):
    def test_integer_grammar_and_near_misses(self):
        self.assertEqual(read_all("+0 -0 001 + - 12x"), [0, 0, 1, Symbol("+"), Symbol("-"), Symbol("12x")])

    def test_nested_quote_expansion(self):
        self.assertEqual(
            read_one("''x"),
            [Symbol("quote"), [Symbol("quote"), Symbol("x")]],
        )

    def test_adjacent_delimiters_form_distinct_tokens(self):
        self.assertEqual(read_all('word"text"()'), [Symbol("word"), "text", []])

    def test_structural_error_locations(self):
        cases = {
            ")": r"unmatched.*1:1",
            "\n (1": r"unclosed.*2:2",
            "\n '": r"quote without.*2:2",
            "1\n2": r"trailing.*2:1",
        }
        for source, pattern in cases.items():
            with self.subTest(source=source), self.assertRaisesRegex(ReaderError, pattern):
                read_one(source)

    def test_canonical_data_round_trip_under_quote(self):
        value = [Symbol("a"), 1, True, False, None, "x\ny", []]
        rendered = format_value(value)
        self.assertEqual(read_one(rendered), value)

    def test_empty_source_and_empty_list_differ(self):
        self.assertEqual(read_all(""), [])
        self.assertEqual(read_all("()"), [[]])

    def test_large_signed_integer_parsing_and_printing_are_process_local(self):
        before = sys.get_int_max_str_digits()
        positive = "7" * 5000
        negative = "-" + positive
        self.assertEqual(format_value(read_one(positive)), positive)
        self.assertEqual(format_value(read_one(negative)), negative)
        self.assertEqual(sys.get_int_max_str_digits(), before)

    def test_integer_digit_limit_has_a_positioned_language_error(self):
        with self.assertRaisesRegex(
            ReaderError, r"integer exceeds 10000 digits at 2:3"
        ):
            read_one("\n  +" + "8" * 10001)

    def test_nesting_limit_covers_lists_and_quote_expansion(self):
        list_at_limit = "(" * 256 + "0" + ")" * 256
        self.assertEqual(format_value(read_one(list_at_limit)), list_at_limit)
        for source in (
            "(" * 257 + "0" + ")" * 257,
            "'" * 257 + "0",
        ):
            with self.subTest(source_kind=source[:1]), self.assertRaisesRegex(
                ReaderError, "maximum nesting depth 256"
            ):
                read_one(source)


if __name__ == "__main__":
    unittest.main()
