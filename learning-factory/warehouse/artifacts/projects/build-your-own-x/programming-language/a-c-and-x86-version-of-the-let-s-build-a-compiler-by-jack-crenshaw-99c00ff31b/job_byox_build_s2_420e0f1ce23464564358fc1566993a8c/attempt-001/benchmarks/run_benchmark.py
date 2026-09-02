#!/usr/bin/env python3
"""Optional, self-checking Pebble timing harness; no result is pre-recorded."""

import argparse
import json
from pathlib import Path
import statistics
import subprocess
import tempfile
import time


def run(argv, timeout=30.0):
    return subprocess.run(
        argv,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=timeout,
    )


def timed(argv, repetitions):
    samples = []
    for _ in range(repetitions):
        started = time.monotonic()
        result = run(argv)
        elapsed = time.monotonic() - started
        if result.returncode != 0:
            raise RuntimeError("timed command failed: %s" % result.stderr)
        samples.append(elapsed)
    return samples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--iterations", type=int, default=100000)
    parser.add_argument("--repetitions", type=int, default=5)
    arguments = parser.parse_args()
    if arguments.iterations < 1 or arguments.iterations > 300000:
        parser.error("--iterations must be in 1..300000")
    if arguments.repetitions < 1 or arguments.repetitions > 30:
        parser.error("--repetitions must be in 1..30")

    binary = arguments.binary.resolve()
    with tempfile.TemporaryDirectory(prefix="pebble-benchmark-") as directory:
        temporary = Path(directory)
        source = temporary / "sum.pb"
        assembly = temporary / "sum.s"
        executable = temporary / "sum"
        source.write_text(
            "let n = %d; let total = 0; "
            "while n > 0 { total = total + n; n = n - 1; } print total;\n"
            % arguments.iterations,
            encoding="utf-8",
        )
        expected = "%d\n" % (arguments.iterations * (arguments.iterations + 1) // 2)

        generated = run([str(binary), "compile", str(source), "-o", str(assembly)])
        if generated.returncode != 0:
            raise RuntimeError("compiler failed: %s" % generated.stderr)
        linked = run([arguments.cc, str(assembly), "-o", str(executable)])
        if linked.returncode != 0:
            raise RuntimeError("linker failed: %s" % linked.stderr)

        for argv in ([str(binary), "eval", str(source)], [str(executable)]):
            checked = run(argv)
            if (checked.returncode, checked.stdout, checked.stderr) != (0, expected, ""):
                raise RuntimeError("correctness check failed for %s" % argv[0])

        interpreter = timed([str(binary), "eval", str(source)], arguments.repetitions)
        compiled = timed([str(executable)], arguments.repetitions)
        print(json.dumps({
            "iterations": arguments.iterations,
            "repetitions": arguments.repetitions,
            "interpreter_seconds": interpreter,
            "interpreter_median_seconds": statistics.median(interpreter),
            "compiled_seconds": compiled,
            "compiled_median_seconds": statistics.median(compiled),
            "scope": "end-to-end process time; compilation excluded",
        }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
