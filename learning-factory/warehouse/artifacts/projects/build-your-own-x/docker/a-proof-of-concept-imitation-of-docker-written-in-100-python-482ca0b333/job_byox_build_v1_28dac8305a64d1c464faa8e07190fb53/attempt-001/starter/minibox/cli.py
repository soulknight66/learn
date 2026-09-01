"""Machine-readable command-line interface."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import sys


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="minibox")
    parser.add_argument("--store", default=".minibox", help="workspace directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    image_import = subparsers.add_parser("image-import")
    image_import.add_argument("image_id")
    image_import.add_argument("layer")

    create = subparsers.add_parser("create")
    create.add_argument("container_id")
    create.add_argument("--image", required=True)
    create.add_argument("--workdir", default="/")
    create.add_argument("--network", action="store_true")
    create.add_argument("--env", action="append", default=[])
    create.add_argument("argv", nargs="*")

    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("container_id")

    events = subparsers.add_parser("events")
    events.add_argument("container_id")

    run = subparsers.add_parser("run")
    run.add_argument("container_id")
    run.add_argument("--timeout", type=float, default=10.0)
    run.add_argument("--max-output", type=int, default=1024 * 1024)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    if "create" in raw_arguments:
        create_index = raw_arguments.index("create")
        try:
            separator = raw_arguments.index("--", create_index + 1)
        except ValueError:
            pass
        else:
            del raw_arguments[separator:]
    build_parser().parse_args(raw_arguments)
    raise NotImplementedError("milestone 5: connect CLI commands to Workspace and Runner")
