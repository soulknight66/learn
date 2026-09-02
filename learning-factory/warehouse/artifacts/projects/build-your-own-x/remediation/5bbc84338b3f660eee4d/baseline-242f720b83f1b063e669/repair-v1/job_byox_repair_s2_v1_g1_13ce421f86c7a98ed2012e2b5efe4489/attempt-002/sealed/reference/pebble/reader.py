"""A positioned tokenizer and recursive-descent reader."""

from dataclasses import dataclass
import re
from typing import Any

from .errors import ReaderError
from .values import Symbol


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    text: str
    line: int
    column: int


_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_SEPARATORS = " \t\r\n,"
_ATOM_DELIMITERS = "()'\";"
_ESCAPES = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t"}
MAX_INTEGER_DIGITS = 10_000
MAX_NESTING_DEPTH = 256
_INTEGER_CHUNK_DIGITS = 9
_INTEGER_CHUNK_BASE = 10**_INTEGER_CHUNK_DIGITS


def _parse_integer(token: Token) -> int:
    """Convert a bounded decimal token without Python's decimal-digit setting."""

    text = token.text
    negative = text.startswith("-")
    digits = text[1:] if text[:1] in "+-" else text
    if len(digits) > MAX_INTEGER_DIGITS:
        raise ReaderError(
            f"integer exceeds {MAX_INTEGER_DIGITS} digits at "
            f"{token.line}:{token.column}"
        )

    first_width = len(digits) % _INTEGER_CHUNK_DIGITS
    if first_width == 0:
        first_width = _INTEGER_CHUNK_DIGITS
    value = int(digits[:first_width])
    for index in range(first_width, len(digits), _INTEGER_CHUNK_DIGITS):
        value = value * _INTEGER_CHUNK_BASE + int(
            digits[index : index + _INTEGER_CHUNK_DIGITS]
        )
    return -value if negative else value


def tokenize(source: str) -> list[Token]:
    """Split source into positioned tokens and decode string contents."""

    if not isinstance(source, str):
        raise TypeError("source must be a string")
    tokens: list[Token] = []
    index = 0
    line = 1
    column = 1

    while index < len(source):
        character = source[index]
        if character in _SEPARATORS:
            if character == "\n":
                line += 1
                column = 1
            else:
                column += 1
            index += 1
            continue
        if character == ";":
            while index < len(source) and source[index] != "\n":
                index += 1
                column += 1
            continue
        if character in "()'":
            kind = {"(": "LPAREN", ")": "RPAREN", "'": "QUOTE"}[character]
            tokens.append(Token(kind, character, line, column))
            index += 1
            column += 1
            continue
        if character == '"':
            start_line, start_column = line, column
            index += 1
            column += 1
            pieces: list[str] = []
            while True:
                if index >= len(source):
                    raise ReaderError(
                        f"unterminated string at {start_line}:{start_column}"
                    )
                character = source[index]
                if character in "\r\n":
                    raise ReaderError(
                        f"raw newline in string at {line}:{column}"
                    )
                if character == '"':
                    index += 1
                    column += 1
                    tokens.append(
                        Token("STRING", "".join(pieces), start_line, start_column)
                    )
                    break
                if character == "\\":
                    escape_column = column
                    if index + 1 >= len(source):
                        raise ReaderError(
                            f"unterminated escape at {line}:{escape_column}"
                        )
                    escaped = source[index + 1]
                    if escaped not in _ESCAPES:
                        raise ReaderError(
                            f"unknown escape \\{escaped} at {line}:{escape_column}"
                        )
                    pieces.append(_ESCAPES[escaped])
                    index += 2
                    column += 2
                    continue
                pieces.append(character)
                index += 1
                column += 1
            continue

        start = index
        start_column = column
        while (
            index < len(source)
            and source[index] not in _SEPARATORS
            and source[index] not in _ATOM_DELIMITERS
        ):
            index += 1
            column += 1
        if index == start:
            raise ReaderError(f"unexpected character {source[index]!r} at {line}:{column}")
        tokens.append(Token("ATOM", source[start:index], line, start_column))

    return tokens


class _TokenReader:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def at_end(self) -> bool:
        return self.index >= len(self.tokens)

    def peek(self) -> Token:
        return self.tokens[self.index]

    def read_form(self, depth: int = 0) -> Any:
        if self.at_end():
            raise ReaderError("expected form at end of input")
        token = self.peek()
        self.index += 1

        if token.kind == "LPAREN":
            if depth >= MAX_NESTING_DEPTH:
                raise ReaderError(
                    f"maximum nesting depth {MAX_NESTING_DEPTH} exceeded at "
                    f"{token.line}:{token.column}"
                )
            values: list[Any] = []
            while True:
                if self.at_end():
                    raise ReaderError(f"unclosed list at {token.line}:{token.column}")
                if self.peek().kind == "RPAREN":
                    self.index += 1
                    return values
                values.append(self.read_form(depth + 1))
        if token.kind == "RPAREN":
            raise ReaderError(f"unmatched ')' at {token.line}:{token.column}")
        if token.kind == "QUOTE":
            if depth >= MAX_NESTING_DEPTH:
                raise ReaderError(
                    f"maximum nesting depth {MAX_NESTING_DEPTH} exceeded at "
                    f"{token.line}:{token.column}"
                )
            if self.at_end():
                raise ReaderError(f"quote without a form at {token.line}:{token.column}")
            return [Symbol("quote"), self.read_form(depth + 1)]
        if token.kind == "STRING":
            return token.text
        if token.kind == "ATOM":
            if _INTEGER.fullmatch(token.text):
                return _parse_integer(token)
            if token.text == "true":
                return True
            if token.text == "false":
                return False
            if token.text == "nil":
                return None
            return Symbol(token.text)
        raise ReaderError(f"invalid token at {token.line}:{token.column}")


def read_one(source: str) -> Any:
    """Read exactly one form or raise ``ReaderError``."""

    reader = _TokenReader(tokenize(source))
    if reader.at_end():
        raise ReaderError("expected one form at 1:1")
    form = reader.read_form()
    if not reader.at_end():
        token = reader.peek()
        raise ReaderError(f"trailing form at {token.line}:{token.column}")
    return form


def read_all(source: str) -> list[Any]:
    """Read every form, returning an empty list for empty source."""

    reader = _TokenReader(tokenize(source))
    forms: list[Any] = []
    while not reader.at_end():
        forms.append(reader.read_form())
    return forms
