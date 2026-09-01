"""Small composition layer for the public API."""

from .compiler import compile_program
from .lexer import tokenize
from .parser import parse
from .vm import run_bytecode


def compile_source(source):
    if not isinstance(source, str):
        raise TypeError("source must be str")
    return compile_program(parse(tokenize(source)))


def run_source(source, stdout, *, step_limit=1_000_000):
    return run_bytecode(compile_source(source), stdout, step_limit=step_limit)


__all__ = ["compile_source", "run_bytecode", "run_source"]
