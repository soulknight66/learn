import argparse
import json
from pathlib import Path
import platform
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--operations", type=int, default=10000)
    args = parser.parse_args()
    if args.operations < 1:
        parser.error("--operations must be positive")

    program = ("0 " + "1 + " * args.operations + ".").encode("ascii")
    started = time.perf_counter_ns()
    result = subprocess.run(
        [str(args.executable.resolve())],
        input=program,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    elapsed = time.perf_counter_ns() - started
    record = {
        "elapsed_ns": elapsed,
        "executable": str(args.executable),
        "machine": platform.machine(),
        "operations_requested": args.operations,
        "returncode": result.returncode,
        "stderr": result.stderr.decode(errors="replace"),
        "stdout_sha256_not_recorded": True,
        "validation_label": "UNVALIDATED_MEASUREMENT",
    }
    print(json.dumps(record, sort_keys=True))
    if result.returncode != 0:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()

