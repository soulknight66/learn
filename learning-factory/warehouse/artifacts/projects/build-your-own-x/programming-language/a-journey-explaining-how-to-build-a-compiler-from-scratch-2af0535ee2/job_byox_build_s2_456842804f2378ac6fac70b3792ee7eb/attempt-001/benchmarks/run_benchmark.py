#!/usr/bin/env python3
"""Bounded compile-plus-execute timing harness; no benchmark is pre-certified."""

from __future__ import print_function

import argparse
import json
import os
import signal
import statistics
import subprocess
import sys
import tempfile
import time


def workload():
    lines = ["let v0 = 1;"]
    for index in range(1, 60):
        lines.append("let v%d = v%d + %d;" % (index, index - 1, index))
    for index in range(190):
        lines.append("print v59 + %d;" % index)
    return ("\n".join(lines) + "\n").encode("ascii")


def timed_run(binary, source_path):
    started = time.perf_counter()
    process = subprocess.Popen(
        [binary, source_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise RuntimeError("benchmark child exceeded five seconds")
    elapsed = time.perf_counter() - started
    if process.returncode != 0:
        raise RuntimeError("child failed: " + stderr.decode("utf-8", "replace"))
    if len(stdout.splitlines()) != 190:
        raise RuntimeError("child produced an unexpected line count")
    return elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True)
    parser.add_argument("--iterations", type=int, default=7)
    parser.add_argument("--warmup", type=int, default=2)
    options = parser.parse_args()
    binary = os.path.abspath(options.binary)
    if not os.path.isfile(binary):
        parser.error("binary does not exist")
    if options.iterations < 1 or options.iterations > 100:
        parser.error("iterations must be between 1 and 100")
    if options.warmup < 0 or options.warmup > 20:
        parser.error("warmup must be between 0 and 20")

    try:
        with tempfile.TemporaryDirectory(prefix="sprig-benchmark-") as directory:
            source_path = os.path.join(directory, "workload.sprig")
            with open(source_path, "wb") as output:
                output.write(workload())
            for unused in range(options.warmup):
                timed_run(binary, source_path)
            samples = [timed_run(binary, source_path)
                       for unused in range(options.iterations)]
    except (OSError, RuntimeError) as error:
        print("benchmark failed: " + str(error), file=sys.stderr)
        return 1

    report = {
        "binary": binary,
        "iterations": options.iterations,
        "median_seconds": statistics.median(samples),
        "samples_seconds": samples,
        "warmup": options.warmup,
        "workload": "60 bindings and 190 print statements",
    }
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
