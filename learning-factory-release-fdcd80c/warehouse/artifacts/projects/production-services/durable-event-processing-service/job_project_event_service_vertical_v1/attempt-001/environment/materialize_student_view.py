from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ALLOWED = (
    "README.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "starter",
    "public_tests",
    "environment/requirements.txt",
)


def materialize(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if source == destination or source in destination.parents:
        raise ValueError("student view must be outside the challenge pack")
    for relative in ALLOWED:
        current = source / relative
        if current.is_symlink() or (
            current.is_dir() and any(path.is_symlink() for path in current.rglob("*"))
        ):
            raise ValueError(f"learner-safe input contains a symlink: {relative}")
    destination.mkdir(parents=True, exist_ok=False)
    for relative in ALLOWED:
        current = source / relative
        target = destination / relative
        if current.is_dir():
            shutil.copytree(current, target)
        elif current.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(current, target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination")
    args = parser.parse_args()
    materialize(Path(__file__).resolve().parents[1], Path(args.destination))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
