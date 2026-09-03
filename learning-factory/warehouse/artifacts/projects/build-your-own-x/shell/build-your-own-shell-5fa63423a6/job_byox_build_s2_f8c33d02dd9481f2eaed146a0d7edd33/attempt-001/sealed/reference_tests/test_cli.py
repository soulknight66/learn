#!/usr/bin/env python3
"""Sealed noninteractive behavior and resource-pressure checks."""

from __future__ import annotations

import os
import pathlib
import resource
import subprocess
import sys
import tempfile


def invoke(binary: pathlib.Path, script: str, *, low_fd_limit: bool = False) -> subprocess.CompletedProcess[str]:
    def limit_descriptors() -> None:
        resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))

    return subprocess.run(
        [str(binary)],
        input=script,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=12.0,
        check=False,
        preexec_fn=limit_descriptors if low_fd_limit else None,
    )


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_cli.py MINISH PROBE", file=sys.stderr)
        return 2
    binary = pathlib.Path(sys.argv[1]).resolve()
    probe = pathlib.Path(sys.argv[2]).resolve()

    result = invoke(binary, "/bin/false\n")
    check(result.returncode == 1, f"false status: {result.returncode}, {result.stderr!r}")

    result = invoke(binary, "definitely-not-a-real-minish-command\n")
    check(result.returncode == 127, f"missing status: {result.returncode}, {result.stderr!r}")

    with tempfile.TemporaryDirectory(prefix="minish-sealed-") as temporary:
        directory = pathlib.Path(temporary)
        output = directory / "out"
        script = (
            f"/usr/bin/printf first > {output}\n"
            f"/usr/bin/printf second >> {output}\n"
            f"/bin/cat < {output}\n"
        )
        result = invoke(binary, script)
        check(result.returncode == 0, f"append status: {result.returncode}, {result.stderr!r}")
        check(result.stdout == "firstsecond", f"append output: {result.stdout!r}")

        result = invoke(binary, f"cd {directory}\n/bin/pwd\n")
        check(result.returncode == 0, f"cd status: {result.returncode}, {result.stderr!r}")
        check(result.stdout.strip() == str(directory), f"cd output: {result.stdout!r}")

        redirected = directory / "wins"
        result = invoke(
            binary,
            f"/usr/bin/printf left > {redirected} | /usr/bin/wc -c\n",
        )
        check(result.returncode == 0, f"precedence status: {result.returncode}, {result.stderr!r}")
        check(result.stdout.strip() == "0", f"precedence pipe output: {result.stdout!r}")
        check(redirected.read_text() == "left", "explicit redirection did not win")

    result = invoke(binary, "exit invalid\n/usr/bin/printf survived\n")
    check(result.returncode == 0, f"invalid exit recovery status: {result.returncode}")
    check(result.stdout == "survived", f"invalid exit recovery output: {result.stdout!r}")

    result = invoke(binary, f"{probe} emit-pgid | {probe} check-pgid\n")
    check(result.returncode == 0, f"pipeline process groups differ: {result.returncode}, {result.stderr!r}")

    pressure_script = "/usr/bin/printf x | /bin/cat > /dev/null\n" * 220
    result = invoke(binary, pressure_script, low_fd_limit=True)
    check(result.returncode == 0, f"descriptor pressure failed: {result.returncode}, {result.stderr[-400:]!r}")

    result = invoke(binary, "exit 255\n")
    check(result.returncode == 255, f"exit 255 status: {result.returncode}")

    print("sealed CLI tests: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, subprocess.TimeoutExpired) as error:
        print(f"sealed CLI tests: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
