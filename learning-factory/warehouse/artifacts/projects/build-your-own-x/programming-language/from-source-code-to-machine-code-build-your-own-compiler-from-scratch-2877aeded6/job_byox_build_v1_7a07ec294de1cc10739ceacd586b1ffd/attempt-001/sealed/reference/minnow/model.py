from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    INT = auto()
    IDENT = auto()
    LET = auto()
    PRINT = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    TRUE = auto()
    FALSE = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    BANG = auto()
    EQUAL_EQUAL = auto()
    BANG_EQUAL = auto()
    LESS = auto()
    LESS_EQUAL = auto()
    GREATER = auto()
    GREATER_EQUAL = auto()
    EQUAL = auto()
    SEMICOLON = auto()
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    lexeme: str
    line: int
    column: int
    value: int | None = None


@dataclass(frozen=True, slots=True)
class Literal:
    value: int
    token: Token


@dataclass(frozen=True, slots=True)
class Variable:
    name: Token


@dataclass(frozen=True, slots=True)
class Unary:
    operator: Token
    right: object


@dataclass(frozen=True, slots=True)
class Binary:
    left: object
    operator: Token
    right: object


@dataclass(frozen=True, slots=True)
class Let:
    name: Token
    initializer: object


@dataclass(frozen=True, slots=True)
class Assign:
    name: Token
    value: object


@dataclass(frozen=True, slots=True)
class Print:
    value: object


@dataclass(frozen=True, slots=True)
class Block:
    statements: tuple


@dataclass(frozen=True, slots=True)
class If:
    condition: object
    then_branch: Block
    else_branch: Block | None


@dataclass(frozen=True, slots=True)
class While:
    condition: object
    body: Block


@dataclass(frozen=True, slots=True)
class Program:
    statements: tuple
