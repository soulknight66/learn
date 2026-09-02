"""Pebble value representations and canonical formatting."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Symbol:
    """A name in source or quoted data; deliberately distinct from ``str``."""

    name: str


def format_value(value: Any) -> str:
    """Return the canonical external representation from REQUIREMENTS.md."""

    raise NotImplementedError("TODO: implement canonical Pebble printing")
