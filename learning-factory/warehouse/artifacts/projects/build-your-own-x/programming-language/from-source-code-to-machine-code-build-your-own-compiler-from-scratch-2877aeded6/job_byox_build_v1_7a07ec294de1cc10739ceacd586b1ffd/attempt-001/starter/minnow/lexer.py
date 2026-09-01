"""Turn source characters into located tokens."""

from .model import TokenKind


KEYWORDS = {
    "let": TokenKind.LET,
    "print": TokenKind.PRINT,
    "if": TokenKind.IF,
    "else": TokenKind.ELSE,
    "while": TokenKind.WHILE,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
}


def tokenize(source):
    """Return a list ending in exactly one EOF token."""
    if not isinstance(source, str):
        raise TypeError("source must be str")
    # TODO: implement scanning, maximal munch, comments, locations, and range checks.
    raise NotImplementedError("implement tokenize")
