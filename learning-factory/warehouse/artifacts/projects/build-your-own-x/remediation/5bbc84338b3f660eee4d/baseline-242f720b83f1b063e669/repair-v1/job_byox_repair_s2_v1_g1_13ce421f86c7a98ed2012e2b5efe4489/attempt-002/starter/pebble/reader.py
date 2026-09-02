"""Tokenizer and recursive reader scaffold."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    text: str
    line: int
    column: int


def tokenize(source: str) -> list[Token]:
    """Split source into positioned tokens, decoding strings as specified."""

    raise NotImplementedError("TODO: implement tokenization")


def read_one(source: str) -> Any:
    """Read exactly one form or raise ReaderError."""

    raise NotImplementedError("TODO: implement single-form reading")


def read_all(source: str) -> list[Any]:
    """Read every form in source, returning an empty list for empty input."""

    raise NotImplementedError("TODO: implement multi-form reading")
