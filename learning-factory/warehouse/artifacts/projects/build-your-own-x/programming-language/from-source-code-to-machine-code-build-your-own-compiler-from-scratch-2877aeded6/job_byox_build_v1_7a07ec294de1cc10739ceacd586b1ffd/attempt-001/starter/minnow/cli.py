"""Command-line adapter. Language implementation lives behind the public API."""

import argparse
import os
from pathlib import Path
import sys
import tempfile

from .api import compile_source, run_bytecode, run_source
from .errors import MiniError


def _positive_integer(text):
    try:
        value = int(text, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def _parser():
    parser = argparse.ArgumentParser(prog="minnow")
    commands = parser.add_subparsers(dest="command", required=True)
    compile_cmd = commands.add_parser("compile")
    compile_cmd.add_argument("source")
    compile_cmd.add_argument("output")
    run_cmd = commands.add_parser("run")
    run_cmd.add_argument("--max-steps", type=_positive_integer, default=1_000_000)
    run_cmd.add_argument("bytecode")
    exec_cmd = commands.add_parser("exec")
    exec_cmd.add_argument("--max-steps", type=_positive_integer, default=1_000_000)
    exec_cmd.add_argument("source")
    return parser


def _atomic_write(path, payload):
    destination = Path(path)
    parent = destination.parent
    descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == "compile":
            source = Path(args.source).read_text(encoding="utf-8", errors="strict")
            _atomic_write(args.output, compile_source(source))
        elif args.command == "run":
            run_bytecode(Path(args.bytecode).read_bytes(), sys.stdout, step_limit=args.max_steps)
        else:
            source = Path(args.source).read_text(encoding="utf-8", errors="strict")
            run_source(source, sys.stdout, step_limit=args.max_steps)
    except (MiniError, OSError, UnicodeError, TypeError, ValueError) as exc:
        print(f"minnow: {exc}", file=sys.stderr)
        return 2
    return 0
