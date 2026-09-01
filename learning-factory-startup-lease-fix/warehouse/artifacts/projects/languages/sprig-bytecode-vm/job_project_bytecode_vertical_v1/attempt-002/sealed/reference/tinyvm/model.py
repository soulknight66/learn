from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


class LanguageError(Exception):
    pass


class LexError(LanguageError):
    pass


class ParseError(LanguageError):
    pass


class CompileError(LanguageError):
    pass


class RuntimeFault(LanguageError):
    pass


class ResourceLimit(RuntimeFault):
    pass


@dataclass(frozen=True)
class Token:
    kind: str
    lexeme: str
    line: int
    column: int


@dataclass(frozen=True)
class Literal:
    value: int


@dataclass(frozen=True)
class Variable:
    name: str


@dataclass(frozen=True)
class Unary:
    operator: str
    right: "Expr"


@dataclass(frozen=True)
class Binary:
    left: "Expr"
    operator: str
    right: "Expr"


Expr: TypeAlias = Literal | Variable | Unary | Binary


@dataclass(frozen=True)
class Let:
    name: str
    initializer: Expr


@dataclass(frozen=True)
class Assign:
    name: str
    value: Expr


@dataclass(frozen=True)
class Print:
    expression: Expr


@dataclass(frozen=True)
class Block:
    statements: tuple["Stmt", ...]


@dataclass(frozen=True)
class If:
    condition: Expr
    then_branch: Block
    else_branch: Block | None


@dataclass(frozen=True)
class While:
    condition: Expr
    body: Block


Stmt: TypeAlias = Let | Assign | Print | Block | If | While


@dataclass(frozen=True)
class Program:
    statements: tuple[Stmt, ...]


@dataclass(frozen=True)
class ExecutionResult:
    outputs: tuple[int, ...]
    globals: dict[str, int]
    steps: int
    engine: str
