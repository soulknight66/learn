#!/usr/bin/env python3
"""Read-only checks for the commands needed by the Mica challenge."""

import platform
import shutil
import subprocess
import sys


def version(command, argument="--version"):
    path = shutil.which(command)
    if path is None:
        print("{}: MISSING".format(command))
        return False
    completed = subprocess.run(
        [path, argument],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        timeout=10,
    )
    first = completed.stdout.splitlines()[0] if completed.stdout else "no version text"
    print("{}: {}".format(command, first))
    return completed.returncode == 0


def main():
    ok = version("cc")
    ok = version("make") and ok
    ok = version("python3") and ok
    machine = platform.machine()
    print("machine: {}".format(machine))
    if machine not in ("x86_64", "AMD64"):
        print("native backend tests require x86-64")
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
