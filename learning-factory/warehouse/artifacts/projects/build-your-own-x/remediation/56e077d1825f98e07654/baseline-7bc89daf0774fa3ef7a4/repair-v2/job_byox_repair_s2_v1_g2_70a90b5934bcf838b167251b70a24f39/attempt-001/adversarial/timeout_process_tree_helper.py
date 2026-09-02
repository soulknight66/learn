#!/usr/bin/env python3
"""Regression helper: create a descendant that would outlive a direct child."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def descendant(ready: Path, escaped: Path) -> int:
    ready.write_text("ready\n", encoding="utf-8")
    time.sleep(1.5)
    escaped.write_text("descendant escaped\n", encoding="utf-8")
    return 0


def parent(ready: Path, escaped: Path) -> int:
    subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--descendant",
            "--ready",
            str(ready),
            "--escaped",
            str(escaped),
        ],
        stdin=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 5.0
    while not ready.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    if not ready.exists():
        return 2
    print("DESCENDANT_READY", flush=True)
    time.sleep(30.0)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--parent", action="store_true")
    mode.add_argument("--descendant", action="store_true")
    parser.add_argument("--ready", required=True, type=Path)
    parser.add_argument("--escaped", required=True, type=Path)
    args = parser.parse_args()
    if args.descendant:
        return descendant(args.ready, args.escaped)
    return parent(args.ready, args.escaped)


if __name__ == "__main__":
    raise SystemExit(main())
