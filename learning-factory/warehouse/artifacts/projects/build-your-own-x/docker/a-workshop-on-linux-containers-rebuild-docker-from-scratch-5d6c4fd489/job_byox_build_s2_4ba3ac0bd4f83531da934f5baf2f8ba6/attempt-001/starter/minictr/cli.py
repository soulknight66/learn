"""Small JSON CLI. Real execution remains deliberately unwired in the starter."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .errors import MiniCtrError
from .spec import ContainerSpec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="minictr")
    parser.add_argument("spec", type=Path, help="path to a JSON container specification")
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.spec.read_text(encoding="utf-8"))
        spec = ContainerSpec.from_mapping(value)
    except (OSError, json.JSONDecodeError, MiniCtrError) as exc:
        print(f"minictr: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(spec.to_mapping(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
