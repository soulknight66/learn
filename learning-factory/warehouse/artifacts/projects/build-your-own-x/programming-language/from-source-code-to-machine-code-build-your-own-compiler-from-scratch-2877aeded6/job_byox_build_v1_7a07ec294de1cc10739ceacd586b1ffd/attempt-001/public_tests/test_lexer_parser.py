import unittest

from minnow.errors import LexError, ParseError
from minnow.lexer import tokenize
from minnow.model import Binary, Print, TokenKind
from minnow.parser import parse


class LexerParserTests(unittest.TestCase):
    def test_comments_keywords_and_longest_operator(self):
        tokens = tokenize("let item2 = 10; // skip\r\nprint item2 != 0;")
        self.assertEqual(
            [token.kind for token in tokens],
            [
                TokenKind.LET,
                TokenKind.IDENT,
                TokenKind.EQUAL,
                TokenKind.INT,
                TokenKind.SEMICOLON,
                TokenKind.PRINT,
                TokenKind.IDENT,
                TokenKind.BANG_EQUAL,
                TokenKind.INT,
                TokenKind.SEMICOLON,
                TokenKind.EOF,
            ],
        )
        self.assertEqual((tokens[5].line, tokens[5].column), (2, 1))

    def test_precedence_builds_multiplication_below_addition(self):
        program = parse(tokenize("print 2 + 3 * 4;"))
        statement = program.statements[0]
        self.assertIsInstance(statement, Print)
        self.assertIsInstance(statement.value, Binary)
        self.assertEqual(statement.value.operator.kind, TokenKind.PLUS)
        self.assertEqual(statement.value.right.operator.kind, TokenKind.STAR)

    def test_unexpected_character_is_located(self):
        with self.assertRaises(LexError) as caught:
            tokenize("print 1;\nprint @;")
        self.assertEqual((caught.exception.line, caught.exception.column), (2, 7))

    def test_missing_semicolon_is_parse_error(self):
        with self.assertRaises(ParseError):
            parse(tokenize("print 1"))


if __name__ == "__main__":
    unittest.main()
