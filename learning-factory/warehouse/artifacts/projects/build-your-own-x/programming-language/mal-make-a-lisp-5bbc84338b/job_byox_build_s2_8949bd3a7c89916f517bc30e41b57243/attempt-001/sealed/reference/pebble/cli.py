"""Command-line interface for Pebble."""

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from .errors import PebbleError
from .interpreter import Interpreter
from .values import format_value


def _report(error: BaseException) -> int:
    print(f"error: {error}", file=sys.stderr)
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pebble")
    parser.add_argument("-e", "--expr", help="evaluate source and print its final value")
    parser.add_argument("file", nargs="?", help="evaluate a UTF-8 Pebble file")
    options = parser.parse_args(argv)
    if options.expr is not None and options.file is not None:
        parser.error("-e/--expr and file are mutually exclusive")

    interpreter = Interpreter()
    try:
        if options.expr is not None:
            print(format_value(interpreter.eval_source(options.expr)))
            return 0
        if options.file is not None:
            source = Path(options.file).read_text(encoding="utf-8")
            interpreter.eval_source(source)
            return 0

        while True:
            try:
                source = input("pebble> ")
            except EOFError:
                return 0
            if not source.strip():
                continue
            print(format_value(interpreter.eval_source(source)))
    except (PebbleError, OSError, UnicodeError) as error:
        return _report(error)


if __name__ == "__main__":
    raise SystemExit(main())
