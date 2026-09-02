#!/usr/bin/env python3
"""Run the sealed ARM identity regression with bounded captured output."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path

MAX_OUTPUT = 65536
REQUIRED = (
    b"REENTRANT-PROBE",
    b"REPLACEMENT-RAN",
    b"RETURN-REPLACEMENT-RAN",
    b"NO-BUG",
)
FORBIDDEN = (
    b"OUTER-RETURN",
    b"BUG-STALE-RETURN-KILLED-REPLACEMENT",
    b"PROBE-SETUP-FAILED",
)


def fail(message: str, output: bytes = b"") -> int:
    if output:
        sys.stdout.buffer.write(output[:MAX_OUTPUT])
        if not output.endswith(b"\n"):
            sys.stdout.buffer.write(b"\n")
    print(f"runtime_reentrancy_qemu: FAIL: {message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qemu", type=Path, required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--library-path", default="")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    if args.timeout <= 0.0:
        return fail("timeout must be positive")
    argv = [
        str(args.qemu),
        "-M",
        "versatilepb",
        "-cpu",
        "arm926",
        "-m",
        "128M",
        "-nographic",
        "-monitor",
        "none",
        "-semihosting-config",
        "enable=on,target=native",
        "-kernel",
        str(args.kernel),
    ]
    environment = os.environ.copy()
    if args.library_path:
        environment["LD_LIBRARY_PATH"] = args.library_path

    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=environment,
        )
    except OSError as error:
        return fail(f"could not start QEMU: {error}")

    try:
        output, _ = process.communicate(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        output, _ = process.communicate()
        return fail(f"timeout after {args.timeout:g} seconds", output)

    if len(output) > MAX_OUTPUT:
        return fail(f"captured output exceeds {MAX_OUTPUT} bytes", output)
    if process.returncode != 0:
        return fail(f"QEMU exited {process.returncode}", output)

    normalized = output.replace(b"\r\n", b"\n")
    previous = -1
    for marker in REQUIRED:
        position = normalized.find(marker)
        if position < 0:
            return fail(f"missing marker {marker.decode('ascii')}", output)
        if position <= previous:
            return fail(f"marker out of order {marker.decode('ascii')}", output)
        previous = position
    for marker in FORBIDDEN:
        if marker in normalized:
            return fail(f"forbidden marker {marker.decode('ascii')}", output)

    sys.stdout.buffer.write(output)
    print("runtime_reentrancy_qemu: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
