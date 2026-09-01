import unittest

from minnow import LexError, ParseError
from minnow.lexer import MAX_I64, tokenize
from minnow.model import Binary, If, Literal, TokenKind, Unary, While
from minnow.parser import parse


class LexerTests(unittest.TestCase):
    def test_empty_source_has_located_eof(self):
        tokens = tokenize("")
        self.assertEqual(len(tokens), 1)
        self.assertIs(tokens[0].kind, TokenKind.EOF)
        self.assertEqual((tokens[0].line, tokens[0].column), (1, 1))

    def test_cr_lf_and_crlf_each_count_once(self):
        tokens = tokenize("\rprint 1;\nprint 2;\r\nprint 3;")
        prints = [token for token in tokens if token.kind is TokenKind.PRINT]
        self.assertEqual([(token.line, token.column) for token in prints], [(2, 1), (3, 1), (4, 1)])

    def test_comment_at_eof_and_division(self):
        tokens = tokenize("print 8 / 2; // no newline")
        self.assertIn(TokenKind.SLASH, [token.kind for token in tokens])
        self.assertEqual(tokens[-1].line, 1)

    def test_every_prefixed_operator_uses_maximal_munch(self):
        tokens = tokenize("! != = == < <= > >=")
        self.assertEqual(
            [token.kind for token in tokens[:-1]],
            [
                TokenKind.BANG,
                TokenKind.BANG_EQUAL,
                TokenKind.EQUAL,
                TokenKind.EQUAL_EQUAL,
                TokenKind.LESS,
                TokenKind.LESS_EQUAL,
                TokenKind.GREATER,
                TokenKind.GREATER_EQUAL,
            ],
        )

    def test_literal_maximum_is_accepted(self):
        token = tokenize(str(MAX_I64))[0]
        self.assertEqual(token.value, MAX_I64)

    def test_literal_above_maximum_is_rejected_at_start(self):
        with self.assertRaises(LexError) as caught:
            tokenize("\n  9223372036854775808")
        self.assertEqual(caught.exception.code, "LEX002")
        self.assertEqual((caught.exception.line, caught.exception.column), (2, 3))

    def test_non_ascii_identifier_and_digit_are_rejected(self):
        for source in ("let café = 1;", "print ١;"):
            with self.subTest(source=source), self.assertRaises(LexError):
                tokenize(source)

    def test_source_type_is_checked(self):
        with self.assertRaises(TypeError):
            tokenize(b"print 1;")


class ParserTests(unittest.TestCase):
    def test_left_associativity(self):
        expression = parse(tokenize("print 9 - 3 - 1;")).statements[0].value
        self.assertIsInstance(expression, Binary)
        self.assertIsInstance(expression.left, Binary)
        self.assertEqual(expression.left.operator.kind, TokenKind.MINUS)

    def test_unary_is_right_associative(self):
        expression = parse(tokenize("print !-1;")).statements[0].value
        self.assertIsInstance(expression, Unary)
        self.assertIsInstance(expression.right, Unary)

    def test_boolean_literal_value(self):
        statements = parse(tokenize("print true; print false;")).statements
        self.assertEqual([statement.value.value for statement in statements], [1, 0])
        self.assertTrue(all(isinstance(statement.value, Literal) for statement in statements))

    def test_if_else_and_while_require_blocks(self):
        program = parse(tokenize("if (true) {} else {} while (false) {}"))
        self.assertIsInstance(program.statements[0], If)
        self.assertIsInstance(program.statements[1], While)
        for source in ("if (true) print 1;", "while (true) print 1;"):
            with self.subTest(source=source), self.assertRaises(ParseError):
                parse(tokenize(source))

    def test_stray_else_and_trailing_expression_are_errors(self):
        for source in ("else {}", "1 + 2;", "print (1 + 2;"):
            with self.subTest(source=source), self.assertRaises(ParseError):
                parse(tokenize(source))


if __name__ == "__main__":
    unittest.main()
