#!/usr/bin/env python3
"""Assemble and link one x86-64 Cinder source file without invoking a shell."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile


DEFAULT_AS = Path("/usr/bin/as")
DEFAULT_LD = Path("/usr/bin/ld.bfd")
TIMEOUT_SECONDS = 20


def run_checked(argv: list[str], *, cwd: Path | None = None) -> None:
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        if stdout:
            sys.stderr.write(stdout)
        if stderr:
            sys.stderr.write(stderr)
        sys.stderr.write(f"tool timed out after {TIMEOUT_SECONDS} seconds: {argv[0]}\n")
        raise SystemExit(124)
    if process.returncode != 0:
        if stdout:
            sys.stderr.write(stdout)
        if stderr:
            sys.stderr.write(stderr)
        raise SystemExit(process.returncode)


def regular_non_symlink(parser: argparse.ArgumentParser, kind: str, supplied: Path) -> Path:
    """Reject a symlink as supplied, then return its absolute regular-file path."""
    try:
        mode = supplied.lstat().st_mode
    except OSError:
        parser.error(f"{kind} must be a regular non-symlink file: {supplied}")
    if not stat.S_ISREG(mode):
        parser.error(f"{kind} must be a regular non-symlink file: {supplied}")

    try:
        resolved = supplied.resolve(strict=True)
    except OSError:
        parser.error(f"{kind} must resolve to a regular file: {supplied}")
    if not resolved.is_file():
        parser.error(f"{kind} must resolve to a regular file: {supplied}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument("--assembler", type=Path, default=DEFAULT_AS)
    parser.add_argument("--linker", type=Path, default=DEFAULT_LD)
    args = parser.parse_args()

    source = regular_non_symlink(parser, "source", args.source)
    output = args.output.resolve()
    assembler = regular_non_symlink(parser, "assembler", args.assembler)
    linker = regular_non_symlink(parser, "linker", args.linker)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".cinder-build-", dir=output.parent) as temporary:
        build_directory = Path(temporary)
        # Keep the linker's object argument stable. GNU ld retains this string in
        # .strtab, so passing the random temporary path would change output bytes.
        object_name = "cinder.o"
        run_checked(
            [str(assembler), "--64", "-o", object_name, str(source)], cwd=build_directory
        )
        run_checked(
            [str(linker), "-m", "elf_x86_64", "-z", "noexecstack", "-o", str(output), object_name],
            cwd=build_directory,
        )
    os.chmod(output, 0o755)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
