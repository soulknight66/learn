from __future__ import annotations

from .lexer import lex
from .model import Assign, Binary, Block, Expr, If, Let, Literal, ParseError, Print, Program, Token, Unary, Variable, While


class Parser:
    def __init__(self, tokens: tuple[Token, ...]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> Program:
        statements = []
        while not self._check("EOF"):
            statements.append(self._statement())
        return Program(tuple(statements))

    def _statement(self):
        if self._match("LET"):
            name = self._consume("IDENT", "expected variable name")
            self._consume("=", "expected '=' after variable name")
            value = self._expression()
            self._consume(";", "expected ';' after declaration")
            return Let(name.lexeme, value)
        if self._match("PRINT"):
            value = self._expression()
            self._consume(";", "expected ';' after value")
            return Print(value)
        if self._match("IF"):
            self._consume("(", "expected '(' after if")
            condition = self._expression()
            self._consume(")", "expected ')' after condition")
            then_branch = self._block()
            else_branch = self._block() if self._match("ELSE") else None
            return If(condition, then_branch, else_branch)
        if self._match("WHILE"):
            self._consume("(", "expected '(' after while")
            condition = self._expression()
            self._consume(")", "expected ')' after condition")
            return While(condition, self._block())
        if self._check("{"):
            return self._block()
        if self._check("IDENT") and self._check_next("="):
            name = self._advance().lexeme
            self._advance()
            value = self._expression()
            self._consume(";", "expected ';' after assignment")
            return Assign(name, value)
        token = self._peek()
        raise ParseError(f"expected statement at {token.line}:{token.column}")

    def _block(self) -> Block:
        self._consume("{", "expected '{'")
        statements = []
        while not self._check("}") and not self._check("EOF"):
            statements.append(self._statement())
        self._consume("}", "expected '}' after block")
        return Block(tuple(statements))

    def _expression(self) -> Expr:
        return self._or()

    def _or(self) -> Expr:
        expression = self._and()
        while self._match("||"):
            expression = Binary(expression, self._previous().kind, self._and())
        return expression

    def _and(self) -> Expr:
        expression = self._equality()
        while self._match("&&"):
            expression = Binary(expression, self._previous().kind, self._equality())
        return expression

    def _equality(self) -> Expr:
        expression = self._comparison()
        while self._match("==", "!="):
            expression = Binary(expression, self._previous().kind, self._comparison())
        return expression

    def _comparison(self) -> Expr:
        expression = self._term()
        while self._match("<", "<=", ">", ">="):
            expression = Binary(expression, self._previous().kind, self._term())
        return expression

    def _term(self) -> Expr:
        expression = self._factor()
        while self._match("+", "-"):
            operator = self._previous().kind
            right = self._factor()
            expression = Binary(expression, operator, right)
        return expression

    def _factor(self) -> Expr:
        expression = self._unary()
        while self._match("*", "/", "%"):
            expression = Binary(expression, self._previous().kind, self._unary())
        return expression

    def _unary(self) -> Expr:
        if self._match("!", "-"):
            return Unary(self._previous().kind, self._unary())
        return self._primary()

    def _primary(self) -> Expr:
        if self._match("NUMBER"):
            token = self._previous()
            significant = token.lexeme.lstrip("0") or "0"
            if len(significant) > 19:
                raise ParseError(f"integer literal exceeds signed 64-bit magnitude at {token.line}:{token.column}")
            try:
                value = int(significant)
            except ValueError as error:
                raise ParseError(f"invalid integer literal at {token.line}:{token.column}") from error
            # INT_MAX + 1 is admitted only so unary minus can spell INT_MIN. All other
            # uses are rejected by checked guest-language evaluation, never host int limits.
            if value > 2 ** 63:
                raise ParseError(f"integer literal exceeds signed 64-bit magnitude at {token.line}:{token.column}")
            return Literal(value)
        if self._match("TRUE"):
            return Literal(1)
        if self._match("FALSE"):
            return Literal(0)
        if self._match("IDENT"):
            return Variable(self._previous().lexeme)
        if self._match("("):
            expression = self._expression()
            self._consume(")", "expected ')' after expression")
            return expression
        token = self._peek()
        raise ParseError(f"expected expression at {token.line}:{token.column}")

    def _match(self, *kinds: str) -> bool:
        if any(self._check(kind) for kind in kinds):
            self._advance()
            return True
        return False

    def _consume(self, kind: str, message: str) -> Token:
        if self._check(kind):
            return self._advance()
        token = self._peek()
        raise ParseError(f"{message} at {token.line}:{token.column}")

    def _check(self, kind: str) -> bool:
        return self._peek().kind == kind

    def _check_next(self, kind: str) -> bool:
        return self.current + 1 < len(self.tokens) and self.tokens[self.current + 1].kind == kind

    def _advance(self) -> Token:
        token = self._peek()
        if token.kind != "EOF":
            self.current += 1
        return token

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]


def parse(source: str) -> Program:
    return Parser(lex(source)).parse()
