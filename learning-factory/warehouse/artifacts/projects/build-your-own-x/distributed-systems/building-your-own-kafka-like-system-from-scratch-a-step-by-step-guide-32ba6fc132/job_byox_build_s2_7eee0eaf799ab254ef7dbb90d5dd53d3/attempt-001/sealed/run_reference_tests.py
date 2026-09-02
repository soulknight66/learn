#!/usr/bin/env python3
"""Compile and run evaluator tests for the sealed implementation."""

from __future__ import annotations

from pathlib import Path
import shlex
import subprocess
import sys
import tempfile


JAVA_HOME = Path(
    "/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11"
)


def run(argv: list[str], repository: Path) -> int:
    print("$ " + shlex.join(argv), flush=True)
    try:
        completed = subprocess.run(
            argv,
            cwd=repository,
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
    repository = Path(__file__).resolve().parents[1]
    javac = JAVA_HOME / "bin" / "javac"
    java = JAVA_HOME / "bin" / "java"
    roots = (
        repository / "sealed" / "reference" / "src" / "main" / "java",
        repository / "public_tests" / "src" / "test" / "java",
        repository / "sealed" / "reference_tests" / "src" / "test" / "java",
        repository / "sealed" / "benchmarks" / "src" / "main" / "java",
    )
    sources = sorted(str(path) for root in roots for path in root.rglob("*.java"))
    with tempfile.TemporaryDirectory(prefix="minilog-reference-build-") as temporary:
        classes = Path(temporary) / "classes"
        classes.mkdir()
        runtime_tmp = Path(temporary) / "runtime-tmp"
        runtime_tmp.mkdir()
        compile_argv = [str(javac), "-encoding", "UTF-8", "-d", str(classes), *sources]
        result = run(compile_argv, repository)
        if result != 0:
            return result
        for main_class in (
            "edu.learningfactory.minilog.PublicTestMain",
            "edu.learningfactory.minilog.ReferenceTestMain",
        ):
            result = run(
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
