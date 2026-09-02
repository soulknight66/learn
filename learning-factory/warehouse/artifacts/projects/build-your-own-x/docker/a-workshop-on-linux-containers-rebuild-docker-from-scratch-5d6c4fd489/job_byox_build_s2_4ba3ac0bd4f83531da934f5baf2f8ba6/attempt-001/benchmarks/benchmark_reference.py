#!/usr/bin/env python3
"""Small reproducible harness; not a production benchmark methodology."""

import argparse
from pathlib import Path
import stat
import tempfile
import time

from minictr.planner import build_launch_plan
from minictr.registry import Registry
from minictr.spec import ContainerSpec


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 10000:
        parser.error("iterations must be between 1 and 10000")

    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        root = base / "root"
        (root / "proc").mkdir(parents=True)
        executable = base / "unshare"
        executable.write_text("benchmark placeholder", encoding="utf-8")
        executable.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        common = {
            "rootfs": str(root),
            "command": ["/bin/true"],
            "timeout_seconds": 1,
        }

        start = time.perf_counter()
        for index in range(args.iterations):
            spec = ContainerSpec.from_mapping({"id": f"p{index}", **common})
            build_launch_plan(spec, str(executable))
        plan_seconds = time.perf_counter() - start

        registry = Registry(base / "state.sqlite3")
        try:
            start = time.perf_counter()
            for index in range(args.iterations):
                spec = ContainerSpec.from_mapping({"id": f"d{index}", **common})
                registry.create(spec, "2026-01-01T00:00:00Z")
                registry.claim_start(spec.container_id, index + 1, "2026-01-01T00:00:01Z")
                registry.finish(spec.container_id, 0, f"/tmp/{spec.container_id}.log", "2026-01-01T00:00:02Z")
            lifecycle_seconds = time.perf_counter() - start
        finally:
            registry.close()

    print(f"iterations={args.iterations}")
    print(f"plan_total_seconds={plan_seconds:.6f}")
    print(f"sqlite_lifecycle_total_seconds={lifecycle_seconds:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
