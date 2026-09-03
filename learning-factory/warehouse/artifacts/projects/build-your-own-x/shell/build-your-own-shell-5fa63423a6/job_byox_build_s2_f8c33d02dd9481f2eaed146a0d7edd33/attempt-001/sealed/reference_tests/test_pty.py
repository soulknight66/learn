#!/usr/bin/env python3
"""Exercise foreground terminal handoff and Ctrl-C through a real PTY."""

from __future__ import annotations

import errno
import os
import pathlib
import pty
import select
import signal
import sys
import time


PROMPT = b"minish$ "


def read_until(master: int, marker: bytes, timeout: float) -> bytes:
    deadline = time.monotonic() + timeout
    received = bytearray()
    while marker not in received:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AssertionError(f"timed out waiting for {marker!r}; received {bytes(received)!r}")
        readable, _, _ = select.select([master], [], [], remaining)
        if not readable:
            continue
        try:
            chunk = os.read(master, 4096)
        except OSError as error:
            if error.errno == errno.EIO:
                break
            raise
        if not chunk:
            break
        received.extend(chunk)
    if marker not in received:
        raise AssertionError(f"PTY closed before {marker!r}; received {bytes(received)!r}")
    return bytes(received)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_pty.py MINISH", file=sys.stderr)
        return 2
    binary = pathlib.Path(sys.argv[1]).resolve()
    child, master = pty.fork()
    if child == 0:
        os.execv(binary, [str(binary)])

    try:
        read_until(master, PROMPT, 3.0)
        started = time.monotonic()
        os.write(master, b"/bin/sleep 3\n")
        time.sleep(0.15)
        os.write(master, b"\x03")
        transcript = read_until(master, PROMPT, 2.0)
        elapsed = time.monotonic() - started
        if elapsed >= 2.5:
            raise AssertionError(f"Ctrl-C did not interrupt foreground job in time ({elapsed:.3f}s)")
        if b"^C" not in transcript:
            raise AssertionError(f"terminal did not echo Ctrl-C: {transcript!r}")
        os.write(master, b"exit 0\n")
        waited, status = os.waitpid(child, 0)
        child = -1
        if waited <= 0 or not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
            raise AssertionError(f"interactive shell exit status {status}")
    finally:
        os.close(master)
        if child > 0:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(child, 0)

    print("sealed PTY test: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"sealed PTY test: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
