from __future__ import annotations

from .model import LexError, Token


KEYWORDS = {
    "let": "LET", "print": "PRINT", "if": "IF", "else": "ELSE",
    "while": "WHILE", "true": "TRUE", "false": "FALSE",
}
SINGLE = set("(){};+-*/%")


def _ascii_letter(character: str) -> bool:
    return "a" <= character <= "z" or "A" <= character <= "Z"


def _ascii_digit(character: str) -> bool:
    return "0" <= character <= "9"


def lex(source: str) -> tuple[Token, ...]:
    tokens: list[Token] = []
    index = 0
    line = 1
    column = 1

    def advance() -> str:
        nonlocal index, line, column
        character = source[index]
        index += 1
        if character == "\n":
            line += 1
            column = 1
        else:
            column += 1
        return character

    while index < len(source):
        character = source[index]
        if character in " \t\r\n":
            advance()
            continue
        if character == "/" and index + 1 < len(source) and source[index + 1] == "/":
            while index < len(source) and source[index] != "\n":
                advance()
            continue
        start_line, start_column = line, column
        if _ascii_digit(character):
            start = index
            while index < len(source) and _ascii_digit(source[index]):
                advance()
            tokens.append(Token("NUMBER", source[start:index], start_line, start_column))
            continue
        if _ascii_letter(character) or character == "_":
            start = index
            while index < len(source) and (
                _ascii_letter(source[index]) or _ascii_digit(source[index]) or source[index] == "_"
            ):
                advance()
            word = source[start:index]
            tokens.append(Token(KEYWORDS.get(word, "IDENT"), word, start_line, start_column))
            continue
        pair = source[index:index + 2]
        if pair in {"==", "!=", "<=", ">=", "&&", "||"}:
            advance(); advance()
            tokens.append(Token(pair, pair, start_line, start_column))
            continue
        if character in SINGLE or character in "=<>!":
            advance()
            tokens.append(Token(character, character, start_line, start_column))
            continue
        raise LexError(f"unexpected character {character!r} at {line}:{column}")
    tokens.append(Token("EOF", "", line, column))
    return tuple(tokens)
