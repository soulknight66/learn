#!/usr/bin/env python3
"""Replayable setup-only probe for the default read-only rootfs policy."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile

from minictr.planner import build_preflight_plan
from minictr.runner import Runner
from minictr.spec import ContainerSpec


def main() -> int:
    temporary_root = os.environ.get("TMPDIR")
    if not temporary_root:
        print(json.dumps({"error": "TMPDIR must name workspace-local scratch"}, sort_keys=True))
        return 2
    dependencies = (
        Path("/bin/true"),
        Path("/lib64/libc.so.6"),
        Path("/lib64/ld-linux-x86-64.so.2"),
    )
    if any(not path.is_file() for path in dependencies):
        print(json.dumps({"error": "expected x86-64 fixture dependencies are missing"}, sort_keys=True))
        return 2
    with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
        root = Path(temporary) / "root"
        (root / "bin").mkdir(parents=True)
        (root / "lib64").mkdir()
        (root / "proc").mkdir()
        for source, target in zip(
            dependencies,
            ("bin/true", "lib64/libc.so.6", "lib64/ld-linux-x86-64.so.2"),
        ):
            shutil.copy2(source, root / target)
        spec = ContainerSpec.from_mapping(
            {
                "id": "readonly",
                "rootfs": str(root.resolve()),
                "command": ["/bin/true"],
                "timeout_seconds": 10,
                "network": False,
            }
        )
        payload = json.dumps(
            spec.to_mapping(), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        result = Runner().run(build_preflight_plan(spec, "/usr/bin/unshare"), payload)
        stderr = result.stderr.decode(errors="replace").strip()
        supported = result.exit_code == 0 and not result.timed_out
        actionable = (
            result.exit_code == 69
            and not result.timed_out
            and "UNSUPPORTED read-only root setup" in stderr
            and "workload was not started" in stderr
        )
        print(
            json.dumps(
                {
                    "actionable_unsupported": actionable,
                    "exit_code": result.exit_code,
                    "supported": supported,
                    "timed_out": result.timed_out,
                    "workload_started": False,
                },
                sort_keys=True,
            )
        )
        return 0 if supported or actionable else 1


if __name__ == "__main__":
    raise SystemExit(main())
