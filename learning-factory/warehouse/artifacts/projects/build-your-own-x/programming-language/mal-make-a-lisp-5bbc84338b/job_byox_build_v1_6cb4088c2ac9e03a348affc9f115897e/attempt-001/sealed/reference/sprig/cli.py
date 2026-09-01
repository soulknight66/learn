"""Command-line driver that keeps language failures out of host tracebacks."""

import argparse
import io
import sys

from .compiler import Compiler
from .errors import LanguageError
from .evaluator import Evaluator
from .printer import print_value
from .reader import read_all
from .runtime import default_environment
from .vm import VirtualMachine


def _parser():
    parser = argparse.ArgumentParser(prog="sprig")
    parser.add_argument("file", nargs="?", help="UTF-8 Sprig source file")
    parser.add_argument("-e", "--expr", help="source text to evaluate")
    parser.add_argument("--engine", choices=("eval", "vm"), default="eval")
    parser.add_argument("--disassemble", action="store_true")
    return parser


def _execute(source, engine, disassemble, output, environment=None, evaluator=None):
    forms = read_all(source)
    if environment is None:
        environment = default_environment()
    if evaluator is None:
        evaluator = Evaluator()
    for form in forms:
        if engine == "eval":
            value = evaluator.evaluate(form, environment)
        else:
            bytecode = Compiler().compile(form)
            if disassemble:
                listing = bytecode.disassemble()
                if listing:
                    output.write(listing + "\n")
            value = VirtualMachine().run(bytecode, environment)
        output.write(print_value(value) + "\n")


def _repl(engine, disassemble, stdin, stdout, stderr):
    environment = default_environment()
    evaluator = Evaluator()
    while True:
        try:
            stdout.write("sprig> ")
            stdout.flush()
            line = stdin.readline()
        except (IOError, KeyboardInterrupt):
            stdout.write("\n")
            return 0
        if line == "":
            return 0
        try:
            _execute(line, engine, disassemble, stdout, environment, evaluator)
        except LanguageError as error:
            stderr.write(str(error) + "\n")
            return 2


def main(argv=None):
    parser = _parser()
    arguments = parser.parse_args(argv)
    if arguments.expr is not None and arguments.file is not None:
        parser.error("-e/--expr and FILE are mutually exclusive")
    if arguments.disassemble and arguments.engine != "vm":
        parser.error("--disassemble requires --engine vm")
    if arguments.expr is None and arguments.file is None:
        return _repl(
            arguments.engine, arguments.disassemble, sys.stdin, sys.stdout, sys.stderr
        )
    try:
        if arguments.expr is not None:
            source = arguments.expr
        else:
            try:
                with io.open(arguments.file, "r", encoding="utf-8") as source_file:
                    source = source_file.read()
            except (IOError, OSError, UnicodeError) as error:
                raise LanguageError(
                    "CLI_FILE", "could not read source file: {0}".format(type(error).__name__)
                )
        _execute(source, arguments.engine, arguments.disassemble, sys.stdout)
        return 0
    except LanguageError as error:
        sys.stderr.write(str(error) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
