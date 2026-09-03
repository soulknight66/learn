#!/usr/bin/env python3
"""Optional microbenchmark driver; not an acceptance test."""

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=50)
    arguments = parser.parse_args()
    if arguments.iterations < 1 or arguments.iterations > 10000:
        parser.error("iterations must be in 1..10000")

    root = Path(__file__).resolve().parents[1]
    binary = str(Path(os.environ.get("MSH_BIN", root / "sealed/reference/msh")).resolve())
    command = "printf x | cat | cat"
    started = time.monotonic_ns()
    for _ in range(arguments.iterations):
        subprocess.run(
            [binary, "-c", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=3,
            check=True,
        )
    elapsed = time.monotonic_ns() - started
    print(json.dumps({
        "binary": binary,
        "elapsed_ns": elapsed,
        "iterations": arguments.iterations,
        "python": platform.python_version(),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
