import unittest

from sprig import LanguageError, Symbol, print_value, read_all, read_one, tokenize


class ReaderBoundaryTests(unittest.TestCase):
    def assert_error(self, source, code, **options):
        with self.assertRaises(LanguageError) as caught:
            read_one(source, **options)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def test_empty_quote_and_trailing_errors(self):
        self.assert_error(" ; only a comment", "READ_EMPTY")
        error = self.assert_error("'", "READ_QUOTE")
        self.assertEqual((error.line, error.column), (1, 1))
        error = self.assert_error("ok next", "READ_TRAILING")
        self.assertEqual((error.line, error.column), (1, 4))

    def test_string_escape_matrix_and_comment_character(self):
        value = read_one('"slash=\\\\ quote=\\\" line=\\n return=\\r tab=\\t ; kept"')
        self.assertEqual(value, 'slash=\\ quote=" line=\n return=\r tab=\t ; kept')
        tokens = tokenize('"first\nsecond" atom')
        self.assertEqual((tokens[1].line, tokens[1].column), (2, 9))

    def test_unterminated_string_points_to_opening_quote(self):
        error = self.assert_error("\n  \"no end", "READ_UNTERMINATED_STRING")
        self.assertEqual((error.line, error.column), (2, 3))

    def test_nested_depth_boundary(self):
        self.assertEqual(read_one("(0)", max_depth=1), [0])
        error = self.assert_error("((0))", "READ_DEPTH", max_depth=1)
        self.assertEqual((error.line, error.column), (1, 2))
        for invalid in (0, -1, True, "2"):
            with self.subTest(invalid=invalid):
                self.assert_error("0", "READ_DEPTH", max_depth=invalid)

    def test_large_integer_is_exact(self):
        source = "9" * 120
        self.assertEqual(read_one(source), int(source))

    def test_read_all_empty_and_multiple(self):
        self.assertEqual(read_all(" , ; comment\n"), [])
        self.assertEqual(read_all("1\n(two)\n'3"), [1, [Symbol("two")], [Symbol("quote"), 3]])

    def test_print_read_round_trip_for_reader_values(self):
        values = [
            None, True, False, 0, -900,
            "quote=\" slash=\\ newline=\n tab=\t snow=☃ backspace=\b",
            Symbol("alpha-beta?"),
            [1, "two", Symbol("three"), [], [False]],
        ]
        for value in values:
            with self.subTest(value=repr(value)):
                self.assertEqual(read_one(print_value(value)), value)

    def test_non_text_source_is_a_language_error(self):
        with self.assertRaises(LanguageError) as caught:
            tokenize(b"bytes")
        self.assertEqual(caught.exception.code, "READ_SOURCE_TYPE")


if __name__ == "__main__":
    unittest.main()
