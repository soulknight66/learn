#!/usr/bin/env python3
"""Fixture that leaves a pipe-holding descendant unless its group is killed."""

import os
from pathlib import Path
import signal
import sys
import time


def main():
    if len(sys.argv) != 3:
        return 64
    ready = Path(sys.argv[1])
    escaped = Path(sys.argv[2])
    child = os.fork()
    if child != 0:
        deadline = time.monotonic() + 1.0
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.005)
        return 0 if ready.exists() else 70

    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    ready.write_text("ready\n", encoding="utf-8")
    time.sleep(1.0)
    escaped.write_text("descendant escaped\n", encoding="utf-8")
    time.sleep(30.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
