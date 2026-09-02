#!/usr/bin/env python3
"""Compile the starter and run public tests without third-party tooling."""

from __future__ import annotations

import argparse
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


DEFAULT_JAVA_HOME = Path(
    "/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11"
)


def run(argv: list[str], cwd: Path) -> int:
    print("$ " + shlex.join(argv), flush=True)
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired as failure:
        print(f"TIMEOUT after {failure.timeout} seconds", file=sys.stderr)
        return 124
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--java-home", type=Path, default=DEFAULT_JAVA_HOME)
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[1]
    javac = args.java_home / "bin" / "javac"
    java = args.java_home / "bin" / "java"
    for executable in (javac, java):
        if not executable.is_file():
            print(f"missing executable: {executable}", file=sys.stderr)
            return 2

    source_roots = (
        repository / "starter" / "src" / "main" / "java",
        repository / "public_tests" / "src" / "test" / "java",
    )
    sources = sorted(
        str(source)
        for root in source_roots
        for source in root.rglob("*.java")
    )
    if not sources:
        print("no Java sources found", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="minilog-public-build-") as temporary:
        classes = Path(temporary) / "classes"
        classes.mkdir()
        runtime_tmp = Path(temporary) / "runtime-tmp"
        runtime_tmp.mkdir()
        compile_argv = [
            str(javac),
            "-encoding",
            "UTF-8",
            "-d",
            str(classes),
            *sources,
        ]
        result = run(compile_argv, repository)
        if result != 0:
            return result
        test_argv = [
            str(java),
            "-ea",
            f"-Djava.io.tmpdir={runtime_tmp}",
            "-cp",
            str(classes),
            "edu.learningfactory.minilog.PublicTestMain",
        ]
        return run(test_argv, repository)


if __name__ == "__main__":
    raise SystemExit(main())
