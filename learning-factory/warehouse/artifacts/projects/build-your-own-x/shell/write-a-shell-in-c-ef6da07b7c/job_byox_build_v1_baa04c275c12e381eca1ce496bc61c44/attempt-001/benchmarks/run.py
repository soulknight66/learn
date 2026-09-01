#!/usr/bin/env python3
"""Emit raw wall-clock benchmark samples without asserting thresholds."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time


SCENARIOS = {
    "external_true": "true\n",
    "three_stage_pipeline": "seq 1 1000 | cat | wc -l\n",
    "parser_growth": "printf '%s' '" + ("x" * 8192) + "' | wc -c\n",
}


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def one_run(shell, script):
    started = time.perf_counter()
    result = subprocess.run(
        [str(shell)],
        input=script,
        universal_newlines=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=10.0,
        check=False,
    )
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        raise RuntimeError("scenario failed with {}: {}".format(result.returncode, result.stderr))
    return elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shell", required=True, type=Path)
    parser.add_argument("--iterations", type=int, default=20)
    arguments = parser.parse_args()
    shell = arguments.shell.resolve()
    if not shell.is_file() or arguments.iterations < 1:
        parser.error("--shell must be a file and --iterations must be positive")

    samples = {}
    for name, script in sorted(SCENARIOS.items()):
        one_run(shell, script)  # unreported warmup
        samples[name] = [one_run(shell, script) for _ in range(arguments.iterations)]

    print(json.dumps({
        "clock": "time.perf_counter",
        "iterations": arguments.iterations,
        "shell": str(shell),
        "shell_sha256": digest(shell),
        "samples_seconds": samples,
        "warmups_per_scenario": 1,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
