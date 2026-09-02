"""Command-line scaffold for milestone 7."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .engine import Docklet
from .errors import PyDockletError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pydocklet")
    parser.add_argument("--root", type=Path, required=True)
    commands = parser.add_subparsers(dest="action", required=True)

    imp = commands.add_parser("import")
    imp.add_argument("name")
    imp.add_argument("layers", type=Path, nargs="+")

    create = commands.add_parser("create")
    create.add_argument("image")
    create.add_argument("command", nargs="+")
    create.add_argument("--env", action="append", default=[])

    start = commands.add_parser("start")
    start.add_argument("container_id")
    start.add_argument("--timeout", type=float, default=5.0)

    inspect = commands.add_parser("inspect")
    inspect.add_argument("container_id")
    commands.add_parser("list")
    return parser


def _jsonable(record: object) -> dict[str, object]:
    data = asdict(record)  # type: ignore[arg-type]
    return {key: str(value) if isinstance(value, Path) else value for key, value in data.items()}


def main(argv: list[str] | None = None) -> int:
    """TODO(7): complete dispatch, environment parsing, JSON normalization, and exit mapping."""
    args = _parser().parse_args(argv)
    try:
        Docklet(args.root)
        raise NotImplementedError("TODO(7): CLI dispatch")
    except PyDockletError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
