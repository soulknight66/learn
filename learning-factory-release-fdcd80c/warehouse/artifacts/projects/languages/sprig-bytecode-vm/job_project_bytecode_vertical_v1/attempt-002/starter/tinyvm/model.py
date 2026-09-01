from __future__ import annotations

from dataclasses import dataclass


class LanguageError(Exception): pass
class LexError(LanguageError): pass
class ParseError(LanguageError): pass
class CompileError(LanguageError): pass
class RuntimeFault(LanguageError): pass
class ResourceLimit(RuntimeFault): pass


@dataclass(frozen=True)
class ExecutionResult:
    outputs: tuple[int, ...]
    globals: dict[str, int]
    steps: int
    engine: str
