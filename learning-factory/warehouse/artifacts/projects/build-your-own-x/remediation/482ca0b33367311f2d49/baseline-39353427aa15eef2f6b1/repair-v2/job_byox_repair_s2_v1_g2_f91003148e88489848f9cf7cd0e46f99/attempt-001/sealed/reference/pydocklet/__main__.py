"""JSON command-line interface for PyDocklet."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .engine import Docklet
from .errors import InvalidProcess, PyDockletError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pydocklet")
    parser.add_argument("--root", type=Path, required=True)
    commands = parser.add_subparsers(dest="action", required=True)

    import_command = commands.add_parser("import")
    import_command.add_argument("name")
    import_command.add_argument("layers", type=Path, nargs="+")

    create = commands.add_parser("create")
    create.add_argument("image")
    create.add_argument("--env", action="append", default=[], metavar="NAME=VALUE")
    create.add_argument("command", nargs="+")

    start = commands.add_parser("start")
    start.add_argument("container_id")
    start.add_argument("--timeout", type=float, default=5.0)

    inspect = commands.add_parser("inspect")
    inspect.add_argument("container_id")
    commands.add_parser("list")
    return parser


def _normalize(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def _parse_env(items: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise InvalidProcess(f"environment entry must be NAME=VALUE: {item!r}")
        name, value = item.split("=", 1)
        if name in result:
            raise InvalidProcess(f"duplicate environment name: {name}")
        result[name] = value
    return result


def _emit(value: Any) -> None:
    print(json.dumps(_normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        engine = Docklet(args.root)
        if args.action == "import":
            result = engine.import_image(args.name, args.layers)
            return_code = 0
        elif args.action == "create":
            command = list(args.command)
            if command and command[0] == "--":
                command.pop(0)
            result = engine.create(args.image, command, _parse_env(args.env))
            return_code = 0
        elif args.action == "start":
            result = engine.start(args.container_id, args.timeout)
            return_code = result.exit_code if result.exit_code is not None else 125
            if return_code < 0 or return_code > 125:
                return_code = 125
        elif args.action == "inspect":
            result = engine.inspect(args.container_id)
            return_code = 0
        else:
            result = engine.list()
            return_code = 0
        _emit(result)
        return return_code
    except PyDockletError as exc:
        print(str(exc).replace("\n", " "), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
