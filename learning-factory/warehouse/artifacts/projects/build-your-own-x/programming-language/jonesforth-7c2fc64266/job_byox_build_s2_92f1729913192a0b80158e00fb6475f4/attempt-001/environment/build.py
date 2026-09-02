#!/usr/bin/env python3
"""Assemble and link one x86-64 Cinder source file without invoking a shell."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile


DEFAULT_AS = Path("/usr/bin/as")
DEFAULT_LD = Path("/usr/bin/ld")
TIMEOUT_SECONDS = 20


def run_checked(argv: list[str]) -> None:
    process = subprocess.Popen(
        argv,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument("--assembler", type=Path, default=DEFAULT_AS)
    parser.add_argument("--linker", type=Path, default=DEFAULT_LD)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    assembler = args.assembler.resolve()
    linker = args.linker.resolve()

    for kind, path in (("source", source), ("assembler", assembler), ("linker", linker)):
        if not path.is_file() or path.is_symlink():
            parser.error(f"{kind} must be a regular non-symlink file: {path}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cinder-build-") as temporary:
        object_path = Path(temporary) / "cinder.o"
        run_checked([str(assembler), "--64", "-o", str(object_path), str(source)])
        run_checked(
            [str(linker), "-m", "elf_x86_64", "-z", "noexecstack", "-o", str(output), str(object_path)]
        )
    os.chmod(output, 0o755)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
