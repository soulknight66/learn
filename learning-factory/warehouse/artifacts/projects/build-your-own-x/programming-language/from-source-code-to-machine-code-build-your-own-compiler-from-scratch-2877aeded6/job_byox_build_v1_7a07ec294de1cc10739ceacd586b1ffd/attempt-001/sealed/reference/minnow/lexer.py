"""Deterministic ASCII-token lexer with Unicode input rejection."""

from .errors import LexError
from .model import Token, TokenKind


MAX_I64 = (1 << 63) - 1

KEYWORDS = {
    "let": TokenKind.LET,
    "print": TokenKind.PRINT,
    "if": TokenKind.IF,
    "else": TokenKind.ELSE,
    "while": TokenKind.WHILE,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
}

SINGLE = {
    "+": TokenKind.PLUS,
    "-": TokenKind.MINUS,
    "*": TokenKind.STAR,
    "/": TokenKind.SLASH,
    "%": TokenKind.PERCENT,
    ";": TokenKind.SEMICOLON,
    "(": TokenKind.LEFT_PAREN,
    ")": TokenKind.RIGHT_PAREN,
    "{": TokenKind.LEFT_BRACE,
    "}": TokenKind.RIGHT_BRACE,
}

PREFIXED = {
    "!": (TokenKind.BANG, TokenKind.BANG_EQUAL),
    "=": (TokenKind.EQUAL, TokenKind.EQUAL_EQUAL),
    "<": (TokenKind.LESS, TokenKind.LESS_EQUAL),
    ">": (TokenKind.GREATER, TokenKind.GREATER_EQUAL),
}


def _is_alpha(character):
    return "A" <= character <= "Z" or "a" <= character <= "z" or character == "_"


def _is_digit(character):
    return "0" <= character <= "9"


class Lexer:
    def __init__(self, source):
        self.source = source
        self.index = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def scan(self):
        while True:
            self._skip_trivia()
            if self._at_end():
                self.tokens.append(Token(TokenKind.EOF, "", self.line, self.column))
                return self.tokens
            self._scan_token()

    def _at_end(self):
        return self.index >= len(self.source)

    def _peek(self, distance=0):
        position = self.index + distance
        if position >= len(self.source):
            return "\0"
        return self.source[position]

    def _take_plain(self):
        character = self.source[self.index]
        self.index += 1
        self.column += 1
        return character

    def _take_newline(self):
        if self._peek() == "\r":
            self.index += 1
            if self._peek() == "\n":
                self.index += 1
        else:
            self.index += 1
        self.line += 1
        self.column = 1

    def _skip_trivia(self):
        while not self._at_end():
            character = self._peek()
            if character in " \t":
                self._take_plain()
            elif character in "\r\n":
                self._take_newline()
            elif character == "/" and self._peek(1) == "/":
                self._take_plain()
                self._take_plain()
                while not self._at_end() and self._peek() not in "\r\n":
                    self._take_plain()
            else:
                return

    def _scan_token(self):
        start = self.index
        line = self.line
        column = self.column
        character = self._take_plain()

        if _is_digit(character):
            while _is_digit(self._peek()):
                self._take_plain()
            lexeme = self.source[start:self.index]
            value = int(lexeme, 10)
            if value > MAX_I64:
                raise LexError("integer literal exceeds signed 64-bit maximum", line=line, column=column, code="LEX002")
            self.tokens.append(Token(TokenKind.INT, lexeme, line, column, value))
            return

        if _is_alpha(character):
            while _is_alpha(self._peek()) or _is_digit(self._peek()):
                self._take_plain()
            lexeme = self.source[start:self.index]
            self.tokens.append(Token(KEYWORDS.get(lexeme, TokenKind.IDENT), lexeme, line, column))
            return

        if character in PREFIXED:
            one, two = PREFIXED[character]
            kind = one
            if self._peek() == "=":
                self._take_plain()
                kind = two
            self.tokens.append(Token(kind, self.source[start:self.index], line, column))
            return

        if character in SINGLE:
            self.tokens.append(Token(SINGLE[character], character, line, column))
            return

        raise LexError(f"unexpected character {character!r}", line=line, column=column)


def tokenize(source):
    if not isinstance(source, str):
        raise TypeError("source must be str")
    return Lexer(source).scan()
