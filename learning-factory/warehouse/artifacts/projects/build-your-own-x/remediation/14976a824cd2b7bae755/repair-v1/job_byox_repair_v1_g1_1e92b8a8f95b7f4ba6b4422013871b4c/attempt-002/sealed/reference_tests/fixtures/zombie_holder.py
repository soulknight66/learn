#!/usr/bin/env python3
"""Hold one exited child unreaped long enough for lifecycle tests."""

import os
import pathlib
import sys
import time


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: zombie_holder.py INFO_FILE RELEASE_FILE", file=sys.stderr)
        return 64

    info_path = pathlib.Path(sys.argv[1])
    release_path = pathlib.Path(sys.argv[2])
    child = os.fork()
    if child == 0:
        os._exit(0)

    try:
        deadline = time.monotonic() + 3.0
        state = ""
        token = ""
        while time.monotonic() < deadline:
            stat = pathlib.Path(f"/proc/{child}/stat").read_text(encoding="ascii")
            fields = stat.rsplit(") ", 1)[1].split()
            state = fields[0]
            token = fields[19]
            if state == "Z":
                break
            time.sleep(0.01)
        if state != "Z":
            print(f"child did not become a zombie; final state={state!r}", file=sys.stderr)
            return 1
        with info_path.open("x", encoding="ascii") as stream:
            stream.write(f"{child} {token} {state}\n")

        deadline = time.monotonic() + 12.0
        while not release_path.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        if not release_path.exists():
            print("timed out waiting for release", file=sys.stderr)
            return 124
        return 0
    finally:
        os.waitpid(child, 0)


if __name__ == "__main__":
    raise SystemExit(main())
