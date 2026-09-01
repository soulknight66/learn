"""A positioned lexer and bounded recursive s-expression parser."""

import re

from .errors import LanguageError
from .values import Symbol


_INTEGER = re.compile(r"^[+-]?[0-9]+$")
_ESCAPES = {
    "\\": "\\",
    '"': '"',
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


class Token(object):
    __slots__ = ("kind", "text", "line", "column")

    def __init__(self, kind, text, line, column):
        self.kind = kind
        self.text = text
        self.line = line
        self.column = column

    def __repr__(self):
        return "Token({0!r}, {1!r}, {2}, {3})".format(
            self.kind, self.text, self.line, self.column
        )


def tokenize(source):
    if not isinstance(source, str):
        raise LanguageError("READ_SOURCE_TYPE", "source must be text")
    tokens = []
    index = 0
    line = 1
    column = 1
    length = len(source)
    while index < length:
        character = source[index]
        if character == "\n":
            index += 1
            line += 1
            column = 1
            continue
        if character in " \t\r,":
            index += 1
            column += 1
            continue
        if character == ";":
            while index < length and source[index] != "\n":
                index += 1
                column += 1
            continue
        if character == "(":
            tokens.append(Token("LPAREN", character, line, column))
            index += 1
            column += 1
            continue
        if character == ")":
            tokens.append(Token("RPAREN", character, line, column))
            index += 1
            column += 1
            continue
        if character == "'":
            tokens.append(Token("QUOTE", character, line, column))
            index += 1
            column += 1
            continue
        if character == '"':
            opening_line = line
            opening_column = column
            index += 1
            column += 1
            decoded = []
            closed = False
            while index < length:
                character = source[index]
                if character == '"':
                    index += 1
                    column += 1
                    closed = True
                    break
                if character == "\\":
                    slash_line = line
                    slash_column = column
                    index += 1
                    column += 1
                    if index >= length:
                        raise LanguageError(
                            "READ_UNTERMINATED_STRING", "string is not terminated",
                            opening_line, opening_column,
                        )
                    escaped = source[index]
                    if escaped not in _ESCAPES:
                        raise LanguageError(
                            "READ_BAD_ESCAPE", "unsupported escape \\{0}".format(escaped),
                            line, column,
                        )
                    decoded.append(_ESCAPES[escaped])
                    index += 1
                    column += 1
                    continue
                if character == "\n":
                    decoded.append(character)
                    index += 1
                    line += 1
                    column = 1
                    continue
                decoded.append(character)
                index += 1
                column += 1
            if not closed:
                raise LanguageError(
                    "READ_UNTERMINATED_STRING", "string is not terminated",
                    opening_line, opening_column,
                )
            tokens.append(Token("STRING", "".join(decoded), opening_line, opening_column))
            continue

        atom_line = line
        atom_column = column
        start = index
        while index < length:
            character = source[index]
            if character in " \t\r\n,()';\"":
                break
            index += 1
            column += 1
        if start == index:
            raise LanguageError(
                "READ_CHARACTER", "unexpected character {0!r}".format(source[index]), line, column
            )
        tokens.append(Token("ATOM", source[start:index], atom_line, atom_column))
    return tokens


def _atom(token):
    if token.kind == "STRING":
        return token.text
    if token.text == "true":
        return True
    if token.text == "false":
        return False
    if token.text == "nil":
        return None
    if _INTEGER.match(token.text):
        try:
            return int(token.text, 10)
        except ValueError:
            raise LanguageError(
                "READ_INTEGER", "invalid integer", token.line, token.column
            )
    return Symbol(token.text)


def _parse(tokens, index, depth, max_depth):
    if index >= len(tokens):
        raise LanguageError("READ_EMPTY", "expected a form")
    token = tokens[index]
    if token.kind == "RPAREN":
        raise LanguageError(
            "READ_UNEXPECTED_CLOSE", "unexpected closing parenthesis", token.line, token.column
        )
    if token.kind == "LPAREN":
        if depth >= max_depth:
            raise LanguageError(
                "READ_DEPTH", "reader nesting limit exceeded", token.line, token.column
            )
        values = []
        cursor = index + 1
        while cursor < len(tokens) and tokens[cursor].kind != "RPAREN":
            value, cursor = _parse(tokens, cursor, depth + 1, max_depth)
            values.append(value)
        if cursor >= len(tokens):
            raise LanguageError(
                "READ_UNCLOSED_LIST", "list is missing a closing parenthesis",
                token.line, token.column,
            )
        return values, cursor + 1
    if token.kind == "QUOTE":
        if depth >= max_depth:
            raise LanguageError(
                "READ_DEPTH", "reader nesting limit exceeded", token.line, token.column
            )
        if index + 1 >= len(tokens):
            raise LanguageError(
                "READ_QUOTE", "quote is missing a form", token.line, token.column
            )
        value, cursor = _parse(tokens, index + 1, depth + 1, max_depth)
        return [Symbol("quote"), value], cursor
    return _atom(token), index + 1


def _validate_depth(max_depth):
    if type(max_depth) is not int or max_depth < 1:
        raise LanguageError("READ_DEPTH", "reader nesting limit must be a positive integer")


def read_one(source, max_depth=200):
    _validate_depth(max_depth)
    tokens = tokenize(source)
    if not tokens:
        raise LanguageError("READ_EMPTY", "expected one form")
    try:
        value, cursor = _parse(tokens, 0, 0, max_depth)
    except RecursionError:
        token = tokens[0]
        raise LanguageError(
            "READ_DEPTH", "reader nesting limit exceeded", token.line, token.column
        )
    if cursor != len(tokens):
        token = tokens[cursor]
        raise LanguageError(
            "READ_TRAILING", "expected exactly one form", token.line, token.column
        )
    return value


def read_all(source, max_depth=200):
    _validate_depth(max_depth)
    tokens = tokenize(source)
    values = []
    cursor = 0
    try:
        while cursor < len(tokens):
            value, cursor = _parse(tokens, cursor, 0, max_depth)
            values.append(value)
    except RecursionError:
        token = tokens[cursor] if cursor < len(tokens) else tokens[-1]
        raise LanguageError(
            "READ_DEPTH", "reader nesting limit exceeded", token.line, token.column
        )
    return values
