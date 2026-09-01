import unittest

from sprig import LanguageError, Symbol, print_value, read_all, read_one, tokenize


class ReaderTests(unittest.TestCase):
    def test_tokens_retain_positions_and_skip_comments(self):
        tokens = tokenize("(alpha, 12) ; ignored\n'\"x\\n\"")
        self.assertEqual(
            [(t.kind, t.text, t.line, t.column) for t in tokens],
            [
                ("LPAREN", "(", 1, 1),
                ("ATOM", "alpha", 1, 2),
                ("ATOM", "12", 1, 9),
                ("RPAREN", ")", 1, 11),
                ("QUOTE", "'", 2, 1),
                ("STRING", "x\n", 2, 2),
            ],
        )

    def test_reader_builds_values_and_quote(self):
        self.assertEqual(
            read_one("'(1 true nil word \"word\")"),
            [Symbol("quote"), [1, True, None, Symbol("word"), "word"]],
        )

    def test_read_all_and_round_trip(self):
        values = read_all("; nothing here\n() \"a\\tb\" false -17")
        self.assertEqual(values, [[], "a\tb", False, -17])
        for value in values:
            self.assertEqual(read_one(print_value(value)), value)

    def test_reader_errors_have_codes_and_locations(self):
        cases = [
            ("\"bad\\q\"", "READ_BAD_ESCAPE", (1, 6)),
            ("(one", "READ_UNCLOSED_LIST", (1, 1)),
            (")", "READ_UNEXPECTED_CLOSE", (1, 1)),
        ]
        for source, code, location in cases:
            with self.subTest(source=source):
                with self.assertRaises(LanguageError) as caught:
                    read_one(source)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual((caught.exception.line, caught.exception.column), location)

    def test_exactly_one_form_and_depth_limit(self):
        with self.assertRaises(LanguageError) as caught:
            read_one("1 2")
        self.assertEqual(caught.exception.code, "READ_TRAILING")
        with self.assertRaises(LanguageError) as caught:
            read_one("(((0)))", max_depth=2)
        self.assertEqual(caught.exception.code, "READ_DEPTH")


if __name__ == "__main__":
    unittest.main()
