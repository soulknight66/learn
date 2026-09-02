"""Pebble value representations and canonical formatting."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .errors import ArityError


@dataclass(frozen=True, slots=True)
class Symbol:
    """A name in source or quoted data; deliberately distinct from ``str``."""

    name: str


@dataclass(eq=False, slots=True)
class Builtin:
    name: str
    function: Callable[[list[Any]], Any] = field(repr=False)
    minimum: int
    maximum: int | None

    def invoke(self, arguments: list[Any]) -> Any:
        count = len(arguments)
        if count < self.minimum or (self.maximum is not None and count > self.maximum):
            if self.maximum is None:
                expected = f"at least {self.minimum}"
            elif self.minimum == self.maximum:
                expected = str(self.minimum)
            else:
                expected = f"{self.minimum} to {self.maximum}"
            raise ArityError(
                f"{self.name}: expected {expected} argument(s), received {count}"
            )
        return self.function(arguments)


@dataclass(eq=False, slots=True)
class UserFunction:
    parameters: tuple[str, ...]
    body: tuple[Any, ...]
    closure: Any = field(repr=False)


def _escape_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def format_value(value: Any) -> str:
    """Return the canonical external representation from REQUIREMENTS.md."""

    if value is None:
        return "nil"
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    if isinstance(value, str):
        return _escape_string(value)
    if isinstance(value, Symbol):
        return value.name
    if isinstance(value, list):
        return "(" + " ".join(format_value(item) for item in value) + ")"
    if isinstance(value, Builtin):
        return f"<builtin:{value.name}>"
    if isinstance(value, UserFunction):
        return "<fn>"
    raise TypeError(f"not a Pebble value: {type(value).__name__}")
