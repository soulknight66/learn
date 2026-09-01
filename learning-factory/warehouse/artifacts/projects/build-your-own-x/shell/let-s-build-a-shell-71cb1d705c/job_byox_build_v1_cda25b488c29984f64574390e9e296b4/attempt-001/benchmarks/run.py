#!/usr/bin/env python3
"""Measure bounded end-to-end minish workloads without reference thresholds."""

from __future__ import print_function

import argparse
import json
import os
import platform
import signal
import statistics
import subprocess
import sys
import time


CASES = [
    ("builtin_pwd", "pwd > /dev/null"),
    ("builtin_list_20", "; ".join(["pwd > /dev/null"] * 20)),
    ("external_true", "/bin/true"),
    ("pipeline_128k",
     "/usr/bin/head -c 131072 /dev/zero | /usr/bin/wc -c > /dev/null"),
    ("pipeline_8",
     "/usr/bin/printf x | /bin/cat | /bin/cat | /bin/cat | /bin/cat | "
     "/bin/cat | /bin/cat | /usr/bin/wc -c > /dev/null"),
    ("background_burst",
     "/bin/true & /bin/true & /bin/true & /bin/true & /bin/true & "
     "/bin/true & /bin/true & /bin/true & jobs > /dev/null"),
]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shell", help="path to the minish executable")
    parser.add_argument("--iterations", type=int, default=15,
                        help="timed samples per workload (default: 15)")
    parser.add_argument("--warmup", type=int, default=2,
                        help="untimed samples per workload (default: 2)")
    parser.add_argument("--timeout", type=float, default=5.0,
                        help="seconds allowed for one sample (default: 5)")
    parser.add_argument("--json", action="store_true",
                        help="write strict JSON instead of a table")
    return parser.parse_args()


def session_groups(session_id):
    """Find every process group in a disposable session."""
    try:
        listing = subprocess.run(
            ["ps", "-e", "-o", "sid=", "-o", "pgid="],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=2,
            check=True)
    except (OSError, subprocess.SubprocessError):
        return {session_id}
    groups = set()
    for row in listing.stdout.splitlines():
        fields = row.split()
        if len(fields) == 2 and fields[0].isdigit() and fields[1].isdigit():
            if int(fields[0]) == session_id and int(fields[1]) > 0:
                groups.add(int(fields[1]))
    return groups


def signal_session(session_id, signal_number):
    for unused_round in range(3):
        groups = session_groups(session_id)
        if not groups:
            return
        for group in groups:
            try:
                os.killpg(group, signal_number)
            except ProcessLookupError:
                pass
        time.sleep(0.01)


def terminate_session(process):
    signal_session(process.pid, signal.SIGTERM)
    signal_session(process.pid, signal.SIGKILL)


def run_once(shell_path, command, timeout):
    started = time.perf_counter()
    process = subprocess.Popen(
        [shell_path, "-c", command],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        start_new_session=True)
    try:
        unused_stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_session(process)
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1.0)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                stream.close()
        raise RuntimeError("sample exceeded {:.3f}s".format(timeout))
    elapsed = time.perf_counter() - started
    if process.returncode != 0:
        detail = stderr.decode("utf-8", "replace").strip()
        raise RuntimeError("status {}{}".format(
            process.returncode, ": " + detail if detail else ""))
    return elapsed


def percentile(sorted_values, fraction):
    index = int(round((len(sorted_values) - 1) * fraction))
    return sorted_values[index]


def summarize(seconds):
    ordered = sorted(seconds)
    return {
        "max_seconds": ordered[-1],
        "median_seconds": statistics.median(ordered),
        "min_seconds": ordered[0],
        "p95_seconds": percentile(ordered, 0.95),
        "samples_seconds": seconds,
    }


def main():
    args = parse_args()
    if args.iterations < 1 or args.warmup < 0 or args.timeout <= 0:
        print("iterations >= 1, warmup >= 0, and timeout > 0 are required",
              file=sys.stderr)
        return 2

    shell_path = os.path.abspath(args.shell)
    if not os.path.isfile(shell_path) or not os.access(shell_path, os.X_OK):
        print("not an executable file: {}".format(shell_path), file=sys.stderr)
        return 2

    results = {}
    try:
        for name, command in CASES:
            for unused in range(args.warmup):
                run_once(shell_path, command, args.timeout)
            samples = [run_once(shell_path, command, args.timeout)
                       for unused in range(args.iterations)]
            results[name] = summarize(samples)
    except RuntimeError as error:
        print("benchmark aborted in {}: {}".format(name, error), file=sys.stderr)
        return 1

    document = {
        "harness": "minish-end-to-end-v1",
        "iterations": args.iterations,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "shell": shell_path,
        "warmup": args.warmup,
        "workloads": results,
    }
    if args.json:
        json.dump(document, sys.stdout, indent=2, sort_keys=True)
        print()
    else:
        print("workload                 median ms     p95 ms     min ms     max ms")
        for name, unused_command in CASES:
            item = results[name]
            print("{:<24} {:>10.3f} {:>10.3f} {:>10.3f} {:>10.3f}".format(
                name,
                item["median_seconds"] * 1000.0,
                item["p95_seconds"] * 1000.0,
                item["min_seconds"] * 1000.0,
                item["max_seconds"] * 1000.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
