from __future__ import annotations

from .compiler import compile_program
from .lexer import lex
from .model import CompileError, ExecutionResult, LanguageError, LexError, ParseError, ResourceLimit, RuntimeFault
from .parser import parse
from .vm import execute

ENGINE = "learner-bytecode"


def parse_source(source: str):
    if not isinstance(source, str): raise TypeError("source must be str")
    return parse(lex(source))


def run_source(source: str, *, max_steps: int = 10_000) -> ExecutionResult:
    return execute(compile_program(parse_source(source)), max_steps=max_steps)
