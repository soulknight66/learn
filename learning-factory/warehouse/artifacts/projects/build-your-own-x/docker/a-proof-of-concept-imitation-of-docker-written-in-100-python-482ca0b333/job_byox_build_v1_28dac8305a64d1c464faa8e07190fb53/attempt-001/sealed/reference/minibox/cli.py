"""Machine-readable command-line interface."""

from __future__ import annotations

import argparse
import base64
from collections.abc import Sequence
from dataclasses import asdict
import json
import sys

from .errors import MiniBoxError
from .models import ContainerSpec
from .runtime import Runner
from .state import ContainerRecord, StateEvent
from .workspace import Workspace


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


def _record(record: ContainerRecord) -> dict[str, object]:
    return {
        "container_id": record.container_id,
        "created_ns": record.created_ns,
        "exit_code": record.exit_code,
        "spec": record.spec.to_dict(),
        "state": record.state.value,
        "updated_ns": record.updated_ns,
    }


def _event(event: StateEvent) -> dict[str, object]:
    return {
        "at_ns": event.at_ns,
        "container_id": event.container_id,
        "exit_code": event.exit_code,
        "from_state": event.from_state.value if event.from_state is not None else None,
        "sequence": event.sequence,
        "to_state": event.to_state.value,
    }


def _environment(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"--env requires NAME=VALUE, got {item!r}")
        name, value = item.split("=", 1)
        result[name] = value
    return result


def _emit(value: object) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main(argv: Sequence[str] | None = None) -> int:
    raw_arguments = list(sys.argv[1:] if argv is None else argv)
    payload_after_separator: list[str] | None = None
    if "create" in raw_arguments:
        create_index = raw_arguments.index("create")
        try:
            separator = raw_arguments.index("--", create_index + 1)
        except ValueError:
            pass
        else:
            payload_after_separator = raw_arguments[separator + 1 :]
            del raw_arguments[separator:]
    try:
        arguments = build_parser().parse_args(raw_arguments)
        if arguments.command == "create" and payload_after_separator is not None:
            arguments.argv = payload_after_separator
        workspace = Workspace(arguments.store)
        if arguments.command == "image-import":
            stats = workspace.import_image(arguments.image_id, arguments.layer)
            _emit({"image_id": arguments.image_id, "stats": asdict(stats)})
        elif arguments.command == "create":
            command = list(arguments.argv)
            if command and command[0] == "--":
                command.pop(0)
            spec = ContainerSpec(
                arguments.container_id,
                arguments.image,
                tuple(command),
                _environment(arguments.env),
                arguments.workdir,
                arguments.network,
            )
            _emit(_record(workspace.create(spec)))
        elif arguments.command == "inspect":
            _emit(_record(workspace.state.get(arguments.container_id)))
        elif arguments.command == "events":
            _emit([_event(event) for event in workspace.state.events(arguments.container_id)])
        elif arguments.command == "run":
            result = Runner(
                workspace.state,
                workspace.rootfs_for,
                timeout=arguments.timeout,
                max_output=arguments.max_output,
            ).run(arguments.container_id)
            _emit(
                {
                    "argv": list(result.argv),
                    "container_id": result.container_id,
                    "output_truncated": result.output_truncated,
                    "returncode": result.returncode,
                    "stderr_b64": base64.b64encode(result.stderr).decode("ascii"),
                    "stdout_b64": base64.b64encode(result.stdout).decode("ascii"),
                    "timed_out": result.timed_out,
                }
            )
        else:  # pragma: no cover - argparse guarantees a known command.
            raise AssertionError(f"unhandled command: {arguments.command}")
        return 0
    except (MiniBoxError, OSError, ValueError) as exc:
        print(
            json.dumps({"error": type(exc).__name__, "message": str(exc)}, sort_keys=True),
            file=sys.stderr,
        )
        return 2
