#!/usr/bin/env python3
"""Opt-in Mica microbenchmark; prints observations, never stored claims."""

import argparse
import json
import os
import statistics
import sys
import time


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from environment.harness import readonly_source, run_process, sanitized_environment


def arithmetic_program(count):
    lines = ["let value = 0;"]
    for index in range(count):
        lines.append("value = (value + {}) % 1000000000;".format(index % 997))
    lines.append("print value;")
    return "\n".join(lines) + "\n"


def loop_program(count):
    return (
        "let remaining = {0};\n"
        "let total = 0;\n"
        "while remaining > 0 {{\n"
        "  total = total + 1;\n"
        "  remaining = remaining - 1;\n"
        "}}\n"
        "print total;\n"
    ).format(count)


def measure(binary, source, repeats, timeout):
    observations = []
    with readonly_source(
        source, filename="workload.mica", prefix="mica-benchmark-"
    ) as attempt:
        directory, path = attempt
        for _ in range(repeats):
            start = time.perf_counter()
            completed = run_process(
                [binary, path],
                timeout=timeout,
                cwd=directory,
                env=sanitized_environment(directory),
            )
            elapsed = time.perf_counter() - start
            if completed.returncode != 0:
                raise RuntimeError(
                    "candidate exited {}: {}".format(
                        completed.returncode, completed.stderr
                    )
                )
            observations.append(elapsed)
    return observations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--statements", type=int, default=1000)
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    if args.repeats < 1 or args.statements < 1 or args.iterations < 1:
        parser.error("counts must be positive")
    binary = os.path.abspath(args.binary)
    if not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        parser.error("--binary must be an executable regular file")

    workloads = {
        "arithmetic": arithmetic_program(args.statements),
        "loop": loop_program(args.iterations),
    }
    report = {"schema_version": 1, "binary": binary, "workloads": {}}
    for name in sorted(workloads):
        values = measure(binary, workloads[name], args.repeats, args.timeout)
        report["workloads"][name] = {
            "seconds_raw": values,
            "seconds_median": statistics.median(values),
        }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
