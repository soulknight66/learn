#!/usr/bin/env python3
"""Small black-box test suite for minish; REQUIREMENTS.md remains authoritative."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile


def invoke(binary: pathlib.Path, script: str, timeout: float = 4.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(binary)],
        input=script,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_cli.py MINISH", file=sys.stderr)
        return 2
    binary = pathlib.Path(sys.argv[1]).resolve()

    result = invoke(binary, "/usr/bin/printf abc | /usr/bin/wc -c\n")
    require(result.returncode == 0, f"pipeline status {result.returncode}: {result.stderr!r}")
    require(result.stdout.strip() == "3", f"pipeline output: {result.stdout!r}")

    result = invoke(binary, "/usr/bin/printf '%s' 'quoted value'\n")
    require(result.returncode == 0, f"quote status {result.returncode}: {result.stderr!r}")
    require(result.stdout == "quoted value", f"quote output: {result.stdout!r}")

    with tempfile.TemporaryDirectory(prefix="minish-public-") as temporary:
        target = pathlib.Path(temporary) / "result.txt"
        result = invoke(
            binary,
            f"/usr/bin/printf payload > {target}\n/bin/cat < {target}\n",
        )
        require(result.returncode == 0, f"redirect status {result.returncode}: {result.stderr!r}")
        require(result.stdout == "payload", f"redirect output: {result.stdout!r}")

    result = invoke(binary, "/usr/bin/printf broken |\n/usr/bin/printf recovered\n")
    require(result.returncode == 0, f"recovery status {result.returncode}: {result.stderr!r}")
    require(result.stdout == "recovered", f"recovery output: {result.stdout!r}")
    require("syntax" in result.stderr.lower(), f"missing syntax diagnostic: {result.stderr!r}")

    result = invoke(binary, "exit 7\n")
    require(result.returncode == 7, f"exit builtin returned {result.returncode}: {result.stderr!r}")

    print("public CLI tests: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, subprocess.TimeoutExpired) as error:
        print(f"public CLI tests: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
