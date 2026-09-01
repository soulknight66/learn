from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    kind: str
    lexeme: str
    line: int
    column: int


def lex(source: str) -> tuple[Token, ...]:
    # TODO(stage 1a): emit located tokens and one EOF token; reject unknown characters.
    raise NotImplementedError("implement lex")
