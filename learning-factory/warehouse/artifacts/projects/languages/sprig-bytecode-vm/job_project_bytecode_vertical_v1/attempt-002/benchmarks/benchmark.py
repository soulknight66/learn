from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
from pathlib import Path


IMPLEMENTATIONS = {"bytecode": "sealed/reference", "treewalk": "alternatives/treewalk"}


def measure(name: str, path: str, samples: int) -> dict[str, object]:
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": path}
    process = subprocess.run(
        [sys.executable, "benchmarks/worker.py", "--samples", str(samples)],
        text=True, capture_output=True, env=environment, timeout=30, check=False,
    )
    if process.returncode:
        raise RuntimeError(f"{name} worker failed: {process.stderr[-500:]}")
    value = json.loads(process.stdout)
    if value["engine"] != name: raise RuntimeError("implementation identity mismatch")
    raw = value["raw_elapsed_ns"]
    value["median_elapsed_ns"] = int(statistics.median(raw))
    value["min_elapsed_ns"] = min(raw)
    value["max_elapsed_ns"] = max(raw)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()
    if not 3 <= arguments.samples <= 50:
        raise SystemExit("samples must be in [3, 50]")
    output = Path(arguments.output)
    allowed = (Path.cwd() / "benchmarks" / "results").resolve()
    try: output.resolve().relative_to(allowed)
    except ValueError: raise SystemExit("output must remain under benchmarks/results/")
    raw_results = {name: measure(name, path, arguments.samples) for name, path in IMPLEMENTATIONS.items()}
    if len({value["pid"] for value in raw_results.values()}) != 2:
        raise SystemExit("architectures were not measured in separate processes")
    report = {
        "schema_version": 1,
        "hypothesis": "The complete public API paths have measurably different end-to-end costs; no dispatch-only or universal winner is asserted.",
        "measurement_scope": "Each timed run_source call includes lexing and parsing for both engines and compilation for bytecode.",
        "parameters": {"samples_per_architecture": arguments.samples, "warmups": 3, "workload": "sum integers 120 through 1", "fixed_order": ["bytecode", "treewalk"]},
        "environment": {
            "python": sys.version, "executable": sys.executable, "implementation": platform.python_implementation(),
            "platform": platform.platform(), "machine": platform.machine(), "processor": platform.processor(),
            "cpu_count": os.cpu_count(), "clock": "time.perf_counter_ns", "network": "not used",
        },
        "command": [sys.executable, "benchmarks/benchmark.py", "--samples", str(arguments.samples), "--output", arguments.output],
        "raw_results": raw_results,
        "interpretation_boundary": "Fixed order, Python overhead, host load, and compile inclusion limit inference; rerun and use a precompiled benchmark before attributing dispatch cost.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({name: result["median_elapsed_ns"] for name, result in raw_results.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
