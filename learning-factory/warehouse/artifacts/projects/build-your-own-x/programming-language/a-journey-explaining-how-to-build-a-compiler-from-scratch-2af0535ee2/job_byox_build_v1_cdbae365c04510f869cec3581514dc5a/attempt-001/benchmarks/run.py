#!/usr/bin/env python3
"""Emit raw local timing samples; this file contains no benchmark claims."""

import csv
import os
import subprocess
import sys
import time


PEBBLE_BIN = os.environ.get("PEBBLE_BIN", "sealed/reference/build/pebble")
CASES = (
    ("arithmetic", "benchmarks/cases/arithmetic.peb"),
    ("branches", "benchmarks/cases/branches.peb"),
    ("loop", "benchmarks/cases/loop.peb"),
)


def main():
    writer = csv.writer(sys.stdout)
    writer.writerow(("case", "sample", "elapsed_ns"))
    for name, path in CASES:
        for sample in range(5):
            started = time.perf_counter()
            result = subprocess.run(
                [PEBBLE_BIN, path],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            elapsed = int((time.perf_counter() - started) * 1000000000)
            if result.returncode != 0:
                sys.stderr.buffer.write(result.stderr)
                return result.returncode
            writer.writerow((name, sample, elapsed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
