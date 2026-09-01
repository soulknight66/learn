from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

import tinyvm


SOURCE = """
    let total = 0;
    let n = 120;
    while (n > 0) { total = total + n; n = n - 1; }
    print total;
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, required=True)
    arguments = parser.parse_args()
    if not 3 <= arguments.samples <= 50:
        raise SystemExit("samples must be in [3, 50]")
    for _ in range(3):
        result = tinyvm.run_source(SOURCE, max_steps=20_000)
    raw = []
    for _ in range(arguments.samples):
        started = time.perf_counter_ns()
        result = tinyvm.run_source(SOURCE, max_steps=20_000)
        elapsed = time.perf_counter_ns() - started
        if elapsed <= 0: raise SystemExit("non-positive monotonic timing")
        if result.outputs != (7260,): raise SystemExit("workload result mismatch")
        raw.append(elapsed)
    print(json.dumps({
        "engine": tinyvm.ENGINE,
        "pid": os.getpid(),
        "raw_elapsed_ns": raw,
        "sample_output_sha256": hashlib.sha256(repr(result.outputs).encode()).hexdigest(),
        "semantic_steps_last_sample": result.steps,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
