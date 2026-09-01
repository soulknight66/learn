"""Thin command-line adapter over the reference implementation."""

from __future__ import annotations

import argparse
import json
import sys

from .config import ContainerSpec, load_spec
from .errors import MiniboxError
from .plan import build_plan
from .runtime import LinuxSubprocessBackend, Runtime
from .state import StateStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="minibox")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="validate a specification")
    check.add_argument("spec")

    plan = commands.add_parser("plan", help="print a namespace launch plan")
    plan.add_argument("spec")
    plan.add_argument("--unshare", default="/usr/bin/unshare")
    plan.add_argument("--python", default="/usr/bin/python3")

    run = commands.add_parser("run", help="attempt a real Linux namespace launch")
    run.add_argument("spec")
    run.add_argument("--id", required=True, dest="container_id")
    run.add_argument("--state-dir", required=True)
    run.add_argument("--unshare")
    run.add_argument("--python")
    return parser


def _spec_summary(spec: ContainerSpec) -> dict[str, object]:
    return {
        "argv": list(spec.argv),
        "env_names": sorted(spec.env),
        "hostname": spec.hostname,
        "network_mode": spec.network_mode,
        "rootfs": str(spec.rootfs),
        "schema_version": spec.schema_version,
        "timeout_seconds": spec.timeout_seconds,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        spec = load_spec(arguments.spec)
        if arguments.command == "check":
            print(json.dumps(_spec_summary(spec), sort_keys=True))
            return 0
        if arguments.command == "plan":
            plan = build_plan(
                spec,
                unshare_path=arguments.unshare,
                python_path=arguments.python,
            )
            print(
                json.dumps(
                    {"argv": list(plan.argv), "namespaces": list(plan.namespaces)},
                    sort_keys=True,
                )
            )
            return 0

        backend = LinuxSubprocessBackend(
            unshare_path=arguments.unshare,
            python_path=arguments.python,
        )
        runtime = Runtime(StateStore(arguments.state_dir), backend)
        result = runtime.run(spec, arguments.container_id)
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
        if result.exit_code < 0:
            return min(255, 128 + abs(result.exit_code))
        return min(255, result.exit_code)
    except (MiniboxError, OSError, ValueError) as exc:
        print(f"minibox: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
