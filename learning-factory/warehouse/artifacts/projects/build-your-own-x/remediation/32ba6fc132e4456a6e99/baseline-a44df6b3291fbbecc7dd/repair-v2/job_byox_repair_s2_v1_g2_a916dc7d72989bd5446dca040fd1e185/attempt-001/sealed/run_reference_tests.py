#!/usr/bin/env python3
"""Compile and run evaluator tests for the sealed implementation."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPOSITORY = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPOSITORY / "environment"))

from process_runner import build_directory, run_process


JAVA_HOME = Path(
    "/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--java-home", type=Path, default=JAVA_HOME)
    parser.add_argument(
        "--temp-root",
        type=Path,
        help="writable scratch parent (defaults to a repository-local or attempt-local directory)",
    )
    args = parser.parse_args()

    repository = REPOSITORY
    javac = args.java_home / "bin" / "javac"
    java = args.java_home / "bin" / "java"
    for executable in (javac, java):
        if not executable.is_file():
            print(f"missing executable: {executable}", file=sys.stderr)
            return 2
    roots = (
        repository / "sealed" / "reference" / "src" / "main" / "java",
        repository / "public_tests" / "src" / "test" / "java",
        repository / "sealed" / "reference_tests" / "src" / "test" / "java",
        repository / "sealed" / "benchmarks" / "src" / "main" / "java",
    )
    sources = sorted(str(path) for root in roots for path in root.rglob("*.java"))
    try:
        with build_directory(
            repository, "minilog-reference-build-", args.temp_root
        ) as temporary:
            classes = temporary / "classes"
            classes.mkdir()
            runtime_tmp = temporary / "runtime-tmp"
            runtime_tmp.mkdir()
            compile_argv = [
                str(javac), "-encoding", "UTF-8", "-d", str(classes), *sources
            ]
            result = run_process(compile_argv, repository)
            if result != 0:
                return result
            for main_class in (
                "edu.learningfactory.minilog.PublicTestMain",
                "edu.learningfactory.minilog.ReferenceTestMain",
            ):
                result = run_process(
                    [
                        str(java),
                        "-ea",
                        f"-Djava.io.tmpdir={runtime_tmp}",
                        "-cp",
                        str(classes),
                        main_class,
                    ],
                    repository,
                )
                if result != 0:
                    return result
    except OSError as failure:
        print(f"temporary build directory unavailable: {failure}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
