#!/usr/bin/env python3
"""Report, but do not install or alter, Pebble's expected build tools."""

import platform
import shutil
import subprocess


def first_line(argv):
    completed = subprocess.run(
        argv, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, timeout=5)
    output = completed.stdout or completed.stderr
    return output.splitlines()[0] if output else f"exit {completed.returncode}"


for tool in ("cc", "make", "python3"):
    path = shutil.which(tool)
    print(f"{tool}: {path or 'MISSING'}")
    if path:
        option = "--version"
        print(f"  {first_line([path, option])}")
print(f"machine: {platform.machine()}")
