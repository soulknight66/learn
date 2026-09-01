from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_store(store_type: type, path: Path, operations: int) -> dict[str, float | int]:
    start = time.perf_counter_ns()
    store = store_type(path, sync=False)
    opened = time.perf_counter_ns()
    for item in range(operations):
        store.set(f"key-{item}".encode(), b"x" * 100)
    written = time.perf_counter_ns()
    for item in range(operations):
        assert store.get(f"key-{item}".encode()) == b"x" * 100
    read = time.perf_counter_ns()
    store.close()
    return {
        "operations": operations,
        "open_ns": opened - start,
        "write_total_ns": written - opened,
        "write_ns_per_op": (written - opened) / operations,
        "read_total_ns": read - written,
        "read_ns_per_op": (read - written) / operations,
        "file_bytes": path.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operations", type=int, default=1000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.operations < 1:
        parser.error("operations must be positive")
    implementations = {
        "reference": ROOT / "sealed/reference/kvstore.py",
        "production": ROOT / "production/implementation/kvstore.py",
    }
    results: dict[str, object] = {
        "schema_version": 1,
        "hypothesis": "Basic instrumentation may add write overhead without changing format size.",
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "parameters": {"operations": args.operations, "value_bytes": 100, "sync": False},
        "raw_results": {},
    }
    with tempfile.TemporaryDirectory() as directory:
        for name, source in implementations.items():
            module = load(f"benchmark_{name}", source)
            results["raw_results"][name] = run_store(
                module.KVStore, Path(directory) / f"{name}.log", args.operations
            )
    raw = results["raw_results"]
    results["summary"] = {
        "production_to_reference_write_ratio": (
            raw["production"]["write_ns_per_op"] / raw["reference"]["write_ns_per_op"]
        ),
        "note": "Smoke result from this execution; rerun and profile before generalizing.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(results["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
