#!/usr/bin/env python3

"""Project and verify the learner-visible subset of a full challenge pack."""

from __future__ import print_function

import argparse
import hashlib
import os
import shutil
import stat
import sys


LEARNER_ROOTS = (
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
LEARNER_FILES = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "environment/README.md",
    "environment/learner_view.py",
)
LEARNER_TREES = (
    "starter",
    "public_tests",
)
LEARNER_DIRECTORIES = (
    "environment",
)


class ProjectionError(Exception):
    pass


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def collect_entry(root, path, relative, entries, recurse=True):
    mode = os.lstat(path).st_mode
    normalized = relative.replace(os.sep, "/")
    if stat.S_ISREG(mode):
        entries[normalized] = {
            "type": "file",
            "sha256": file_hash(path),
        }
        return
    if not stat.S_ISDIR(mode):
        raise ProjectionError("non-regular entry selected: {}".format(normalized))

    entries[normalized] = {"type": "directory"}
    if not recurse:
        return
    with os.scandir(path) as iterator:
        children = sorted(iterator, key=lambda entry: entry.name)
    for child in children:
        child_relative = os.path.relpath(child.path, root)
        collect_entry(root, child.path, child_relative, entries)


def source_inventory(source_root):
    source = os.path.abspath(source_root)
    if os.path.islink(source) or not os.path.isdir(source):
        raise ProjectionError("source root must be a real directory")

    entries = {}
    for relative in LEARNER_FILES + LEARNER_TREES:
        path = os.path.join(source, *relative.split("/"))
        if not os.path.lexists(path):
            raise ProjectionError("learner path is missing: {}".format(relative))
        collect_entry(source, path, relative, entries)
    for relative in LEARNER_DIRECTORIES:
        path = os.path.join(source, *relative.split("/"))
        if not os.path.lexists(path):
            raise ProjectionError("learner directory is missing: {}".format(relative))
        collect_entry(source, path, relative, entries, recurse=False)
    return entries


def view_inventory(view_root):
    view = os.path.abspath(view_root)
    if os.path.islink(view) or not os.path.isdir(view):
        raise ProjectionError("learner view must be a real directory")

    entries = {}
    with os.scandir(view) as iterator:
        children = sorted(iterator, key=lambda entry: entry.name)
    for child in children:
        collect_entry(view, child.path, child.name, entries)
    return entries


def compare_inventories(expected, observed):
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    changed = sorted(
        path for path in set(expected) & set(observed)
        if expected[path] != observed[path]
    )
    if missing or extra or changed:
        details = []
        if missing:
            details.append("missing={}".format(",".join(missing)))
        if extra:
            details.append("extra={}".format(",".join(extra)))
        if changed:
            details.append("changed={}".format(",".join(changed)))
        raise ProjectionError("learner view mismatch: {}".format("; ".join(details)))


def inventory_counts(entries):
    files = sum(1 for entry in entries.values() if entry["type"] == "file")
    directories = sum(
        1 for entry in entries.values() if entry["type"] == "directory"
    )
    return files, directories


def paths_overlap(left, right):
    try:
        common = os.path.commonpath((left, right))
    except ValueError:
        return False
    return common == left or common == right


def project(source_root, destination_root):
    source = os.path.abspath(source_root)
    destination = os.path.abspath(destination_root)
    if paths_overlap(os.path.realpath(source), os.path.realpath(destination)):
        raise ProjectionError("source and destination must not overlap")
    if os.path.lexists(destination):
        raise ProjectionError("destination must not already exist")

    expected = source_inventory(source)
    os.mkdir(destination, 0o755)
    ordered = sorted(expected, key=lambda path: (path.count("/"), path))
    for relative in ordered:
        source_path = os.path.join(source, *relative.split("/"))
        destination_path = os.path.join(destination, *relative.split("/"))
        if expected[relative]["type"] == "directory":
            os.mkdir(destination_path, 0o755)
        else:
            shutil.copyfile(source_path, destination_path)
            os.chmod(destination_path, 0o644)

    observed = view_inventory(destination)
    compare_inventories(expected, observed)
    return inventory_counts(observed)


def verify(source_root, view_root):
    expected = source_inventory(source_root)
    observed = view_inventory(view_root)
    compare_inventories(expected, observed)
    return inventory_counts(observed)


def parser():
    result = argparse.ArgumentParser(
        description="Create or verify an exact learner-only challenge view."
    )
    commands = result.add_subparsers(dest="command", required=True)

    project_command = commands.add_parser("project")
    project_command.add_argument("--source", required=True)
    project_command.add_argument("--destination", required=True)

    verify_command = commands.add_parser("verify")
    verify_command.add_argument("--source", required=True)
    verify_command.add_argument("--view", required=True)
    return result


def main(argv=None):
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "project":
            files, directories = project(arguments.source, arguments.destination)
            action = "projection"
        else:
            files, directories = verify(arguments.source, arguments.view)
            action = "verification"
    except (OSError, ProjectionError) as error:
        print("learner_view: FAIL ({})".format(error), file=sys.stderr)
        return 1

    print(
        "learner_view_{}: PASS ({} regular files, {} directories, 0 other entries)".format(
            action,
            files,
            directories,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
