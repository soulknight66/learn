#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")
    started = time.time()
    process = subprocess.run(command, cwd=args.cwd, text=True, capture_output=True, check=False)
    payload = {
        "argv": command,
        "cwd": str(args.cwd.resolve()),
        "started_at": started,
        "elapsed_seconds": time.time() - started,
        "exit_code": process.returncode,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "stdout": process.stdout,
        "stderr": process.stderr,
        "stdout_sha256": hashlib.sha256(process.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(process.stderr.encode()).hexdigest(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
