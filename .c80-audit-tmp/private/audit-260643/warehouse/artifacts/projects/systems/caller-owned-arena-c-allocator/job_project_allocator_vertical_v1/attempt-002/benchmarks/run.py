from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURES = ["reference", "best-fit", "segregated-bins"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    raw_results: dict[str, object] = {}
    commands: dict[str, list[str]] = {}
    for name in ARCHITECTURES:
        argv = [str(ROOT / "validation-output/bin" / f"{name}-benchmark")]
        commands[name] = [f"validation-output/bin/{name}-benchmark"]
        completed = subprocess.run(
            argv,
            cwd=ROOT,
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
            },
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=20,
        )
        if completed.returncode != 0:
            raise SystemExit(
                f"benchmark {name} failed: exit={completed.returncode} stderr={completed.stderr}"
            )
        raw_results[name] = json.loads(completed.stdout)
    toolchain = json.loads(
        (ROOT / "validation-output/toolchain.json").read_text(encoding="utf-8")
    )
    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": (
            "segregated bins should reduce search work under mixed sizes, while first-fit "
            "and best-fit may produce different external fragmentation; smoke data is not "
            "a universal ranking"
        ),
        "parameters": {
            "timed_operations": 80000,
            "arena_bytes": 2097152,
            "slot_count": 256,
            "fragmentation_pattern": "900 deterministic replacements then free even slots",
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "compiler": toolchain["compiler"],
            "strict_flags": toolchain["strict_flags"],
            "network": "not used",
        },
        "commands": commands,
        "raw_results": raw_results,
        "interpretation_boundary": (
            "One bounded in-process smoke workload on this machine; allocator metadata, "
            "cache state, compiler, and timer resolution affect results. Re-run and profile "
            "before drawing production conclusions."
        ),
    }
    output = arguments.output
    if not output.is_absolute():
        output = ROOT / output
    output.resolve().relative_to((ROOT / "benchmarks").resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        name: round(float(value["operations_per_second"]), 3)
        for name, value in raw_results.items()
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
