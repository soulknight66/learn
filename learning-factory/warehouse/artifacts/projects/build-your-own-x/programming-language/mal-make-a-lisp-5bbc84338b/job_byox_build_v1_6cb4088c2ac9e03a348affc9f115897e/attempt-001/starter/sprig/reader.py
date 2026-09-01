"""Tokenizer and s-expression reader (milestone 1)."""


class Token(object):
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
    """Return positioned tokens for source. Implement in milestone 1."""
    raise NotImplementedError("milestone 1: tokenize")


def read_one(source, max_depth=200):
    """Read exactly one form. Implement in milestone 1."""
    raise NotImplementedError("milestone 1: read_one")


def read_all(source, max_depth=200):
    """Read zero or more forms. Implement in milestone 1."""
    raise NotImplementedError("milestone 1: read_all")
