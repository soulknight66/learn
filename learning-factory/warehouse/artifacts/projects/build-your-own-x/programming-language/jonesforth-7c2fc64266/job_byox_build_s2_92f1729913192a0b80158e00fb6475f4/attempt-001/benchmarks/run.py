#!/usr/bin/env python3
"""Run a small process-level Cinder workload and emit explicitly unvalidated JSON."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import time


def invoke(binary: Path, source: bytes, timeout: float) -> int:
    started = time.perf_counter_ns()
    argv = [str(binary)]
    process = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(source, timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise
    elapsed = time.perf_counter_ns() - started
    if process.returncode != 0 or stderr or stdout != b"":
        raise RuntimeError(
            f"workload failed: rc={process.returncode}, stdout={stdout!r}, stderr={stderr!r}"
        )
    return elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--iterations", type=int, default=15)
    parser.add_argument("--terms", type=int, default=1000)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    if args.iterations < 1 or args.terms < 1 or args.timeout <= 0:
        parser.error("iterations, terms, and timeout must be positive")
    binary = args.executable.resolve()
    if not binary.is_file():
        parser.error(f"executable is not a regular file: {binary}")

    # Each term leaves no stack residue and produces no output.
    source = b": sq dup * ; " + (b"17 sq drop " * args.terms)
    invoke(binary, source, args.timeout)  # unreported warmup
    samples = [invoke(binary, source, args.timeout) for _ in range(args.iterations)]
    report = {
        "executable": str(binary),
        "iterations": args.iterations,
        "maximum_ns": max(samples),
        "median_ns": int(statistics.median(samples)),
        "minimum_ns": min(samples),
        "provenance": "benchmarks/run.py generated : sq plus repeated evaluation workload",
        "terms_per_process": args.terms,
        "validation_label": "UNVALIDATED_MEASUREMENT",
    }
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
