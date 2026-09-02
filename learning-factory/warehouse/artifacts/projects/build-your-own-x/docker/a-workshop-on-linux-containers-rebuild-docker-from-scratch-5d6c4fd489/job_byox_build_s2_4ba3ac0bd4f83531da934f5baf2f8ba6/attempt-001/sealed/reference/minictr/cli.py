"""Reference plan/run CLI with explicit execution opt-in."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from .errors import MiniCtrError
from .planner import build_launch_plan
from .runner import Runner
from .spec import ContainerSpec


def _load(path: Path) -> ContainerSpec:
    return ContainerSpec.from_mapping(json.loads(path.read_text(encoding="utf-8")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="minictr-reference")
    parser.add_argument("mode", choices=("plan", "run"))
    parser.add_argument("spec", type=Path)
    parser.add_argument("--unshare", default=shutil.which("unshare"))
    parser.add_argument("--allow-execution", action="store_true")
    args = parser.parse_args(argv)
    try:
        spec = _load(args.spec)
        plan = build_launch_plan(spec, args.unshare or "")
        if args.mode == "plan":
            print(json.dumps({"argv": list(plan.argv), "timeout_seconds": plan.timeout_seconds}, sort_keys=True))
            return 0
        if not args.allow_execution:
            parser.error("run requires --allow-execution")
        payload = json.dumps(spec.to_mapping(), sort_keys=True, separators=(",", ":")).encode()
        result = Runner().run(plan, payload)
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
        if result.timed_out:
            print("minictr: workload timed out", file=sys.stderr)
        return result.exit_code
    except (OSError, json.JSONDecodeError, MiniCtrError) as exc:
        print(f"minictr: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
