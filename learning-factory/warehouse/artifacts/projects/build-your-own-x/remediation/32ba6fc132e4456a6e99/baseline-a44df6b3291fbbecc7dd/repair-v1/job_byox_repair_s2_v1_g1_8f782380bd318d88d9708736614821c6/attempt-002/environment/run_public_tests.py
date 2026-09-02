#!/usr/bin/env python3
"""Compile the starter and run public tests without third-party tooling."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from process_runner import build_directory, run_process


DEFAULT_JAVA_HOME = Path(
    "/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--java-home", type=Path, default=DEFAULT_JAVA_HOME)
    parser.add_argument(
        "--temp-root",
        type=Path,
        help="writable scratch parent (defaults to a repository-local or attempt-local directory)",
    )
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

    try:
        with build_directory(
            repository, "minilog-public-build-", args.temp_root
        ) as temporary:
            classes = temporary / "classes"
            classes.mkdir()
            runtime_tmp = temporary / "runtime-tmp"
            runtime_tmp.mkdir()
            compile_argv = [
                str(javac),
                "-encoding",
                "UTF-8",
                "-d",
                str(classes),
                *sources,
            ]
            result = run_process(compile_argv, repository)
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
            return run_process(test_argv, repository)
    except OSError as failure:
        print(f"temporary build directory unavailable: {failure}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
