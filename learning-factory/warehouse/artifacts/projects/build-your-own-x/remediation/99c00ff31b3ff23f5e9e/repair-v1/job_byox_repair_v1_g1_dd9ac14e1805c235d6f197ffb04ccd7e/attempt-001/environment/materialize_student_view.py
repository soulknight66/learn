#!/usr/bin/env python3
"""Materialize the exact learner-visible projection from a complete pack."""

import os
from pathlib import Path
import shutil
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
VISIBLE_ROOTS = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "starter",
    "public_tests",
    "environment",
)


def within(candidate, parent):
    candidate_text = os.path.abspath(str(candidate))
    parent_text = os.path.abspath(str(parent))
    try:
        return os.path.commonpath((candidate_text, parent_text)) == parent_text
    except ValueError:
        return False


def collect_sources():
    directories = []
    files = []
    for relative_text in VISIBLE_ROOTS:
        relative = Path(relative_text)
        source = ROOT / relative
        if not source.exists() or source.is_symlink():
            raise ValueError("missing or symbolic allowlisted path: {}".format(relative_text))
        mode = source.lstat().st_mode
        if stat.S_ISREG(mode):
            files.append(relative)
            continue
        if not stat.S_ISDIR(mode):
            raise ValueError("non-regular allowlisted path: {}".format(relative_text))
        directories.append(relative)
        for current, names, filenames in os.walk(str(source), followlinks=False):
            names.sort()
            filenames.sort()
            current_path = Path(current)
            for name in names:
                child = current_path / name
                child_mode = child.lstat().st_mode
                child_relative = child.relative_to(ROOT)
                if not stat.S_ISDIR(child_mode) or child.is_symlink():
                    raise ValueError(
                        "symbolic or special source path: {}".format(child_relative)
                    )
                directories.append(child_relative)
            for name in filenames:
                child = current_path / name
                child_mode = child.lstat().st_mode
                child_relative = child.relative_to(ROOT)
                if not stat.S_ISREG(child_mode) or child.is_symlink():
                    raise ValueError(
                        "symbolic or special source path: {}".format(child_relative)
                    )
                files.append(child_relative)
    return sorted(set(directories), key=lambda item: str(item)), sorted(
        set(files), key=lambda item: str(item)
    )


def main():
    if len(sys.argv) != 2:
        print("usage: materialize_student_view.py TARGET", file=sys.stderr)
        return 2

    requested = Path(sys.argv[1])
    target = requested if requested.is_absolute() else ROOT / requested
    target = Path(os.path.abspath(str(target)))
    if target.exists() or target.is_symlink():
        print("FAIL: target already exists: {}".format(requested), file=sys.stderr)
        return 1
    if target == ROOT:
        print("FAIL: target must differ from the pack root", file=sys.stderr)
        return 1
    for relative_text in VISIBLE_ROOTS:
        source = ROOT / relative_text
        if within(target, source) or within(source, target):
            print(
                "FAIL: target overlaps allowlisted source: {}".format(relative_text),
                file=sys.stderr,
            )
            return 1

    try:
        directories, files = collect_sources()
        target.mkdir(parents=True)
        for relative in directories:
            (target / relative).mkdir(parents=True, exist_ok=True)
        for relative in files:
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(ROOT / relative), str(destination))
    except (OSError, ValueError) as error:
        print("FAIL: {}".format(error), file=sys.stderr)
        return 1

    print(
        "student-view: materialized {0} allowlisted roots and {1} regular files at {2}".format(
            len(VISIBLE_ROOTS), len(files), requested
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
