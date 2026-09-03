#!/usr/bin/env python3
"""Compile and run the first learner milestone without requiring a parser."""

import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from environment.process_runner import run


CC = os.environ.get("CC", "cc")
LEXER_SOURCE = Path(os.environ.get(
    "PEBBLE_LEXER_SOURCE", str(ROOT / "starter" / "src" / "lexer.c"))).resolve()


def main():
    if not LEXER_SOURCE.is_file():
        print("missing lexer source: %s" % LEXER_SOURCE, file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="pebble-lexer-") as directory:
        executable = Path(directory) / "lexer_smoke"
        compiled = run([
            CC, "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
            "-I", str(ROOT / "starter" / "include"),
            str(ROOT / "public_tests" / "lexer_smoke.c"),
            str(LEXER_SOURCE), "-o", str(executable),
        ])
        if compiled.returncode != 0:
            sys.stdout.write(compiled.stdout)
            sys.stderr.write(compiled.stderr)
            return compiled.returncode
        checked = run([str(executable)])
        sys.stdout.write(checked.stdout)
        sys.stderr.write(checked.stderr)
        return checked.returncode


if __name__ == "__main__":
    raise SystemExit(main())
