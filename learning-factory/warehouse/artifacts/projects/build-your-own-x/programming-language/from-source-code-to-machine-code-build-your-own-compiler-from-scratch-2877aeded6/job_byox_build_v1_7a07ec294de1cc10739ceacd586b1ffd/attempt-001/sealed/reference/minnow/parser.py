"""Recursive-descent parser with explicit precedence levels."""

from .errors import ParseError
from .model import Assign, Binary, Block, If, Let, Literal, Print, Program, TokenKind, Unary, Variable, While


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current = 0

    def parse_program(self):
        statements = []
        while not self._check(TokenKind.EOF):
            statements.append(self._statement())
        self._consume(TokenKind.EOF, "expected end of input")
        return Program(tuple(statements))

    def _statement(self):
        if self._match(TokenKind.LET):
            return self._let_statement()
        if self._match(TokenKind.PRINT):
            return self._print_statement()
        if self._match(TokenKind.IF):
            return self._if_statement()
        if self._match(TokenKind.WHILE):
            return self._while_statement()
        if self._check(TokenKind.IDENT) and self._check_next(TokenKind.EQUAL):
            return self._assign_statement()
        self._error(self._peek(), "expected statement")

    def _let_statement(self):
        name = self._consume(TokenKind.IDENT, "expected name after 'let'")
        self._consume(TokenKind.EQUAL, "expected '=' after declaration name")
        initializer = self._expression()
        self._consume(TokenKind.SEMICOLON, "expected ';' after declaration")
        return Let(name, initializer)

    def _assign_statement(self):
        name = self._consume(TokenKind.IDENT, "expected assignment name")
        self._consume(TokenKind.EQUAL, "expected '=' after assignment name")
        value = self._expression()
        self._consume(TokenKind.SEMICOLON, "expected ';' after assignment")
        return Assign(name, value)

    def _print_statement(self):
        value = self._expression()
        self._consume(TokenKind.SEMICOLON, "expected ';' after value")
        return Print(value)

    def _if_statement(self):
        self._consume(TokenKind.LEFT_PAREN, "expected '(' after 'if'")
        condition = self._expression()
        self._consume(TokenKind.RIGHT_PAREN, "expected ')' after condition")
        then_branch = self._block()
        else_branch = self._block() if self._match(TokenKind.ELSE) else None
        return If(condition, then_branch, else_branch)

    def _while_statement(self):
        self._consume(TokenKind.LEFT_PAREN, "expected '(' after 'while'")
        condition = self._expression()
        self._consume(TokenKind.RIGHT_PAREN, "expected ')' after condition")
        return While(condition, self._block())

    def _block(self):
        self._consume(TokenKind.LEFT_BRACE, "expected '{' before block")
        statements = []
        while not self._check(TokenKind.RIGHT_BRACE) and not self._check(TokenKind.EOF):
            statements.append(self._statement())
        self._consume(TokenKind.RIGHT_BRACE, "expected '}' after block")
        return Block(tuple(statements))

    def _expression(self):
        return self._equality()

    def _equality(self):
        expression = self._comparison()
        while self._match(TokenKind.EQUAL_EQUAL, TokenKind.BANG_EQUAL):
            operator = self._previous()
            expression = Binary(expression, operator, self._comparison())
        return expression

    def _comparison(self):
        expression = self._term()
        while self._match(TokenKind.LESS, TokenKind.LESS_EQUAL, TokenKind.GREATER, TokenKind.GREATER_EQUAL):
            operator = self._previous()
            expression = Binary(expression, operator, self._term())
        return expression

    def _term(self):
        expression = self._factor()
        while self._match(TokenKind.PLUS, TokenKind.MINUS):
            operator = self._previous()
            expression = Binary(expression, operator, self._factor())
        return expression

    def _factor(self):
        expression = self._unary()
        while self._match(TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT):
            operator = self._previous()
            expression = Binary(expression, operator, self._unary())
        return expression

    def _unary(self):
        if self._match(TokenKind.BANG, TokenKind.MINUS):
            return Unary(self._previous(), self._unary())
        return self._primary()

    def _primary(self):
        if self._match(TokenKind.INT):
            token = self._previous()
            return Literal(token.value, token)
        if self._match(TokenKind.TRUE):
            token = self._previous()
            return Literal(1, token)
        if self._match(TokenKind.FALSE):
            token = self._previous()
            return Literal(0, token)
        if self._match(TokenKind.IDENT):
            return Variable(self._previous())
        if self._match(TokenKind.LEFT_PAREN):
            expression = self._expression()
            self._consume(TokenKind.RIGHT_PAREN, "expected ')' after expression")
            return expression
        self._error(self._peek(), "expected expression")

    def _match(self, *kinds):
        for kind in kinds:
            if self._check(kind):
                self._advance()
                return True
        return False

    def _consume(self, kind, message):
        if self._check(kind):
            return self._advance()
        self._error(self._peek(), message)

    def _check(self, kind):
        return self._peek().kind is kind

    def _check_next(self, kind):
        if self.current + 1 >= len(self.tokens):
            return False
        return self.tokens[self.current + 1].kind is kind

    def _advance(self):
        token = self._peek()
        if self.current < len(self.tokens):
            self.current += 1
        return token

    def _peek(self):
        return self.tokens[self.current]

    def _previous(self):
        return self.tokens[self.current - 1]

    @staticmethod
    def _error(token, message):
        raise ParseError(message, line=token.line, column=token.column)


def parse(tokens):
    return Parser(tokens).parse_program()
