import unittest

from pebble import ReaderError, Symbol, read_all, read_one


class ReaderContractTests(unittest.TestCase):
    def test_literals_and_nested_list(self):
        self.assertEqual(
            read_one('(alpha -12 true false nil "stone")'),
            [Symbol("alpha"), -12, True, False, None, "stone"],
        )

    def test_comments_commas_and_quote_sugar(self):
        self.assertEqual(
            read_all("; heading\n'gem, (1 ; inside\n 2)"),
            [[Symbol("quote"), Symbol("gem")], [1, 2]],
        )

    def test_string_escapes(self):
        self.assertEqual(read_one(r'"a\\b\n\t\"c\""'), 'a\\b\n\t"c"')

    def test_read_all_accepts_empty_source(self):
        self.assertEqual(read_all("  ; only a comment\n, "), [])

    def test_read_one_rejects_empty_and_trailing_forms(self):
        for source in ("", "1 2"):
            with self.subTest(source=source), self.assertRaises(ReaderError):
                read_one(source)

    def test_reader_rejects_structural_and_string_errors(self):
        for source in ("(", ")", "'", r'"bad\q"', '"raw\nnewline"'):
            with self.subTest(source=source), self.assertRaises(ReaderError):
                read_one(source)


if __name__ == "__main__":
    unittest.main()
