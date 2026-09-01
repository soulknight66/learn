from __future__ import annotations

from .interpreter import execute
from .model import CompileError, ExecutionResult, LanguageError, LexError, ParseError, ResourceLimit, RuntimeFault
from .parser import parse

ENGINE = "treewalk"


def parse_source(source: str):
    if not isinstance(source, str): raise TypeError("source must be str")
    return parse(source)


def run_source(source: str, *, max_steps: int = 10_000) -> ExecutionResult:
    return execute(parse_source(source), max_steps=max_steps)
