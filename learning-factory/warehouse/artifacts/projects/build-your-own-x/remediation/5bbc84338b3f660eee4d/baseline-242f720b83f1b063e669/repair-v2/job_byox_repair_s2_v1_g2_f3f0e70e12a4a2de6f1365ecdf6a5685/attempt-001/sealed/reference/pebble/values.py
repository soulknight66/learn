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


def _format_integer(value: int) -> str:
    """Format an integer without Python's decimal-digit safety setting."""

    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    remaining = -value if value < 0 else value
    pieces: list[int] = []
    while remaining:
        remaining, piece = divmod(remaining, 1_000_000_000)
        pieces.append(piece)
    return sign + str(pieces[-1]) + "".join(
        f"{piece:09d}" for piece in reversed(pieces[:-1])
    )


def format_value(value: Any) -> str:
    """Return the canonical external representation from REQUIREMENTS.md."""

    pieces: list[str] = []
    operations: list[tuple[str, Any]] = [("value", value)]
    while operations:
        operation, current = operations.pop()
        if operation == "text":
            pieces.append(current)
        elif current is None:
            pieces.append("nil")
        elif type(current) is bool:
            pieces.append("true" if current else "false")
        elif type(current) is int:
            pieces.append(_format_integer(current))
        elif isinstance(current, str):
            pieces.append(_escape_string(current))
        elif isinstance(current, Symbol):
            pieces.append(current.name)
        elif isinstance(current, list):
            pieces.append("(")
            operations.append(("text", ")"))
            for index in range(len(current) - 1, -1, -1):
                operations.append(("value", current[index]))
                if index:
                    operations.append(("text", " "))
        elif isinstance(current, Builtin):
            pieces.append(f"<builtin:{current.name}>")
        elif isinstance(current, UserFunction):
            pieces.append("<fn>")
        else:
            raise TypeError(f"not a Pebble value: {type(current).__name__}")
    return "".join(pieces)
