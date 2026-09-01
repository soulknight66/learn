#!/usr/bin/env python3
"""Fail-closed validation for a control-plane-created learner view.

The validator reads but never creates or modifies the supplied directory. It
supports Python 3.6 and newer and accepts exactly one learner-view path.
"""

import hashlib
import os
from pathlib import Path
import stat
import sys


PACK_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_PATH = PACK_ROOT / "environment/student-view-files.txt"


class ValidationError(RuntimeError):
    pass


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while True:
            block = source.read(65536)
            if not block:
                return digest.hexdigest()
            digest.update(block)


def read_allowlist():
    try:
        entries = ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ValidationError("cannot read export allowlist: {}".format(error))
    if not entries or entries != sorted(entries) or len(entries) != len(set(entries)):
        raise ValidationError("export allowlist must be non-empty, sorted, and unique")
    for entry in entries:
        path = Path(entry)
        if (not entry or path.is_absolute() or "." in path.parts
                or ".." in path.parts or "sealed" in path.parts):
            raise ValidationError("unsafe export allowlist entry: {!r}".format(entry))
        source = PACK_ROOT / path
        if not source.is_file() or source.is_symlink():
            raise ValidationError("allowlisted source is not a regular file: {}".format(entry))
    return entries


def expected_directories(entries):
    directories = set()
    for entry in entries:
        parent = Path(entry).parent
        while parent != Path("."):
            directories.add(parent.as_posix())
            parent = parent.parent
    return directories


def view_inventory(view_root):
    if view_root.is_symlink() or not view_root.is_dir():
        raise ValidationError("learner view root must be a real directory")

    files = set()
    directories = set()
    for directory, directory_names, file_names in os.walk(str(view_root), followlinks=False):
        current = Path(directory)
        for name in directory_names:
            path = current / name
            mode = path.lstat().st_mode
            if not stat.S_ISDIR(mode):
                raise ValidationError(
                    "non-directory entry in directory position: {}".format(
                        path.relative_to(view_root).as_posix()))
            directories.add(path.relative_to(view_root).as_posix())
        for name in file_names:
            path = current / name
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode):
                raise ValidationError(
                    "learner view contains a non-regular file: {}".format(
                        path.relative_to(view_root).as_posix()))
            files.add(path.relative_to(view_root).as_posix())
    return files, directories


def describe_difference(expected, actual):
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    parts = []
    if missing:
        parts.append("missing=" + ",".join(missing))
    if extra:
        parts.append("extra=" + ",".join(extra))
    return "; ".join(parts)


def validate(view_root):
    entries = read_allowlist()
    expected_files = set(entries)
    expected_dirs = expected_directories(entries)
    actual_files, actual_dirs = view_inventory(view_root)

    if actual_files != expected_files:
        raise ValidationError(
            "learner-view file inventory mismatch: "
            + describe_difference(expected_files, actual_files))
    if actual_dirs != expected_dirs:
        raise ValidationError(
            "learner-view directory inventory mismatch: "
            + describe_difference(expected_dirs, actual_dirs))

    changed = []
    for entry in entries:
        if file_hash(PACK_ROOT / entry) != file_hash(view_root / entry):
            changed.append(entry)
    if changed:
        raise ValidationError("learner-view files differ from pack: " + ", ".join(changed))

    print(
        "PASS learner view: {} regular files, {} directories, exact hashes".format(
            len(actual_files), len(actual_dirs)))


def main(argv):
    if len(argv) != 2:
        print("usage: python3 sealed/validation/verify_student_view.py VIEW_DIRECTORY", file=sys.stderr)
        return 2
    try:
        validate(Path(argv[1]))
    except (OSError, ValidationError) as error:
        print("FAIL {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
