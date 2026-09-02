"""Stable language-level exception types."""


class PebbleError(Exception):
    """Base class for errors safe to show to a Pebble user."""


class ReaderError(PebbleError):
    """Malformed source text."""


class EvalError(PebbleError):
    """Invalid runtime operation or special form."""


class ArityError(EvalError):
    """A function or form received the wrong number of arguments."""


class NameResolutionError(EvalError):
    """A symbol was absent from its lexical environment chain."""
