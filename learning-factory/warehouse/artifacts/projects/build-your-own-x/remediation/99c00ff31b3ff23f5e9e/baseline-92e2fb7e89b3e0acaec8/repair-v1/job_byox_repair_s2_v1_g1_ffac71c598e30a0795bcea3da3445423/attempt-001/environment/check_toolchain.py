#!/usr/bin/env python3
"""Report, but do not install or alter, Pebble's expected build tools."""

import platform
import shutil

try:
    from .process_runner import run
except ImportError:
    from process_runner import run


def first_line(argv):
    completed = run(argv, timeout=5)
    output = completed.stdout or completed.stderr
    return output.splitlines()[0] if output else f"exit {completed.returncode}"


for tool in ("cc", "make", "python3"):
    path = shutil.which(tool)
    print(f"{tool}: {path or 'MISSING'}")
    if path:
        option = "--version"
        print(f"  {first_line([path, option])}")
print(f"machine: {platform.machine()}")
