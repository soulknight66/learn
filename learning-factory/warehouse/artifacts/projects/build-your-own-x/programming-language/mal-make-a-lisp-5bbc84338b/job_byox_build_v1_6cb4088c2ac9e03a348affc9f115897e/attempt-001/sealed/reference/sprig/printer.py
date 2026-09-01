"""Deterministic, readable Sprig value rendering."""

from .errors import LanguageError
from .values import Symbol, UserFunction


def print_value(value):
    if value is None:
        return "nil"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if type(value) is int:
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\")
        escaped = escaped.replace('"', '\\"')
        escaped = escaped.replace("\n", "\\n")
        escaped = escaped.replace("\r", "\\r")
        escaped = escaped.replace("\t", "\\t")
        return '"' + escaped + '"'
    if isinstance(value, Symbol):
        return value.name
    if isinstance(value, list):
        return "(" + " ".join(print_value(item) for item in value) + ")"
    if isinstance(value, UserFunction):
        return "<function>"
    if getattr(value, "_sprig_builtin", False):
        return "<builtin:{0}>".format(value.name)
    raise LanguageError(
        "PRINT_TYPE", "cannot print host value of type {0}".format(type(value).__name__)
    )
