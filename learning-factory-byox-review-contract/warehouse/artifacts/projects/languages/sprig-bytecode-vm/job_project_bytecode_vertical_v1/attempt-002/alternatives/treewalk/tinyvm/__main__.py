from __future__ import annotations

import argparse
import json
import sys

from . import LanguageError, run_source


def main() -> int:
    parser = argparse.ArgumentParser(description="run a Sprig program")
    parser.add_argument("path", help="source file or - for stdin")
    parser.add_argument("--max-steps", type=int, default=10_000)
    arguments = parser.parse_args()
    source = sys.stdin.read() if arguments.path == "-" else open(arguments.path, encoding="utf-8").read()
    try:
        result = run_source(source, max_steps=arguments.max_steps)
    except (LanguageError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps({"engine": result.engine, "outputs": result.outputs, "globals": result.globals, "steps": result.steps}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
