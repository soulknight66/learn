#!/usr/bin/env python3
"""Construct or verify the exact learner-visible view for a worker harness."""

from __future__ import print_function

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LEARNER_TOP_FILES = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
)
LEARNER_DIRS = ("starter", "public_tests", "environment")

ARTIFACT_TOP_FILES = LEARNER_TOP_FILES + (
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "VALIDATION.md",
)
ARTIFACT_DIRS = LEARNER_DIRS + (
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
)

FORBIDDEN_VIEW_PARTS = frozenset((
    "sealed",
    "reference",
    "reference_tests",
    "hidden_tests",
    "solution",
    "solutions",
    "answer",
    "answers",
))


class ViewPolicyError(Exception):
    pass


def _relative(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def _require_regular(path, label):
    try:
        mode = os.lstat(path).st_mode
    except OSError as error:
        raise ViewPolicyError("cannot inspect {0}: {1}".format(label, error))
    if not stat.S_ISREG(mode) or stat.S_ISLNK(mode):
        raise ViewPolicyError("not a regular file: " + label)


def _collect_files(top_files, directories):
    result = []
    for relative in top_files:
        path = os.path.join(ROOT, relative)
        _require_regular(path, relative)
        result.append(relative)
    for relative_dir in directories:
        base = os.path.join(ROOT, relative_dir)
        try:
            base_mode = os.lstat(base).st_mode
        except OSError as error:
            raise ViewPolicyError("cannot inspect {0}: {1}".format(relative_dir, error))
        if not stat.S_ISDIR(base_mode) or stat.S_ISLNK(base_mode):
            raise ViewPolicyError("not a real directory: " + relative_dir)
        for current, dirnames, filenames in os.walk(base, followlinks=False):
            dirnames.sort()
            filenames.sort()
            for dirname in dirnames:
                directory = os.path.join(current, dirname)
                mode = os.lstat(directory).st_mode
                if not stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
                    raise ViewPolicyError("non-directory entry: " + _relative(directory, ROOT))
            for filename in filenames:
                path = os.path.join(current, filename)
                relative = _relative(path, ROOT)
                _require_regular(path, relative)
                result.append(relative)
    return tuple(sorted(set(result)))


def _collect_directories(root, directories):
    result = []
    for relative_dir in directories:
        base = os.path.join(root, *relative_dir.split("/"))
        try:
            mode = os.lstat(base).st_mode
        except OSError as error:
            raise ViewPolicyError("cannot inspect {0}: {1}".format(relative_dir, error))
        if not stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
            raise ViewPolicyError("not a real directory: " + relative_dir)
        for current, dirnames, unused_filenames in os.walk(base, followlinks=False):
            del unused_filenames
            dirnames.sort()
            relative = _relative(current, root)
            result.append(relative)
            for dirname in dirnames:
                path = os.path.join(current, dirname)
                child_mode = os.lstat(path).st_mode
                if not stat.S_ISDIR(child_mode) or stat.S_ISLNK(child_mode):
                    raise ViewPolicyError("non-directory entry: " + _relative(path, root))
    return tuple(sorted(set(result)))


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(65536)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _hashes(root, paths):
    return dict((relative, _sha256(os.path.join(root, relative))) for relative in paths)


def _learner_files():
    paths = _collect_files(LEARNER_TOP_FILES, LEARNER_DIRS)
    directories = _collect_directories(ROOT, LEARNER_DIRS)
    for relative in paths + directories:
        parts = relative.split("/")
        if any(part.lower() in FORBIDDEN_VIEW_PARTS for part in parts):
            raise ViewPolicyError("forbidden learner-view path: " + relative)
    return paths


def check_policy():
    learner = _learner_files()
    artifact = _collect_files(ARTIFACT_TOP_FILES, ARTIFACT_DIRS)
    excluded = tuple(sorted(set(artifact) - set(learner)))
    sealed = tuple(path for path in excluded if path == "sealed" or path.startswith("sealed/"))
    learner_hashes = set(_hashes(ROOT, learner).values())
    sealed_hashes = set(_hashes(ROOT, sealed).values())
    collisions = learner_hashes.intersection(sealed_hashes)
    if collisions:
        raise ViewPolicyError(
            "learner-visible content duplicates {0} sealed file hash(es)".format(len(collisions))
        )
    return {
        "excluded_artifact_files": len(excluded),
        "learner_files": len(learner),
        "sealed_content_hash_collisions": 0,
    }


def _destination_entries(destination):
    if not os.path.isdir(destination):
        raise ViewPolicyError("learner view is not a directory: " + destination)
    paths = []
    directories = []
    for current, dirnames, filenames in os.walk(destination, followlinks=False):
        dirnames.sort()
        filenames.sort()
        for dirname in dirnames:
            path = os.path.join(current, dirname)
            mode = os.lstat(path).st_mode
            if not stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
                raise ViewPolicyError("non-directory in learner view: " + _relative(path, destination))
            relative = _relative(path, destination)
            if any(part.lower() in FORBIDDEN_VIEW_PARTS for part in relative.split("/")):
                raise ViewPolicyError("forbidden directory in learner view: " + relative)
            directories.append(relative)
        for filename in filenames:
            path = os.path.join(current, filename)
            relative = _relative(path, destination)
            _require_regular(path, "learner view/" + relative)
            paths.append(relative)
    return tuple(sorted(paths)), tuple(sorted(directories))


def verify_view(destination):
    expected = _learner_files()
    expected_directories = _collect_directories(ROOT, LEARNER_DIRS)
    actual, actual_directories = _destination_entries(destination)
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise ViewPolicyError("view file set differs; missing={0!r}, extra={1!r}".format(missing, extra))
    if actual_directories != expected_directories:
        missing = sorted(set(expected_directories) - set(actual_directories))
        extra = sorted(set(actual_directories) - set(expected_directories))
        raise ViewPolicyError(
            "view directory set differs; missing={0!r}, extra={1!r}".format(missing, extra)
        )
    source_hashes = _hashes(ROOT, expected)
    destination_hashes = _hashes(destination, actual)
    changed = [path for path in expected if source_hashes[path] != destination_hashes[path]]
    if changed:
        raise ViewPolicyError("view content differs from allowlisted source: " + ", ".join(changed))
    check_policy()
    return {"learner_files": len(actual), "verified_exact_copy": True}


def export_view(destination):
    destination = os.path.abspath(destination)
    source = os.path.realpath(ROOT)
    resolved_destination = os.path.realpath(destination)
    if resolved_destination == source or resolved_destination.startswith(source + os.sep):
        raise ViewPolicyError("destination must be outside the challenge artifact")
    if os.path.lexists(destination):
        raise ViewPolicyError("destination must not already exist")
    expected = _learner_files()
    expected_directories = _collect_directories(ROOT, LEARNER_DIRS)
    check_policy()
    os.makedirs(destination, 0o755)
    for relative in expected_directories:
        directory = os.path.join(destination, *relative.split("/"))
        if not os.path.isdir(directory):
            os.makedirs(directory, 0o755)
    for relative in expected:
        source_path = os.path.join(ROOT, relative)
        destination_path = os.path.join(destination, *relative.split("/"))
        parent = os.path.dirname(destination_path)
        if not os.path.isdir(parent):
            os.makedirs(parent, 0o755)
        shutil.copyfile(source_path, destination_path)
        os.chmod(destination_path, 0o644)
    return verify_view(destination)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    subparsers.add_parser("check-policy", help="validate the source allowlist without exporting")
    subparsers.add_parser("list", help="print the exact learner-visible file list")
    export_parser = subparsers.add_parser("export", help="copy the allowlist to a new directory")
    export_parser.add_argument("destination")
    verify_parser = subparsers.add_parser("verify", help="verify a previously exported directory")
    verify_parser.add_argument("destination")
    arguments = parser.parse_args(argv)

    if arguments.command == "check-policy":
        print(json.dumps(check_policy(), sort_keys=True))
    elif arguments.command == "list":
        check_policy()
        for relative in _learner_files():
            print(relative)
    elif arguments.command == "export":
        print(json.dumps(export_view(arguments.destination), sort_keys=True))
    elif arguments.command == "verify":
        print(json.dumps(verify_view(os.path.abspath(arguments.destination)), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ViewPolicyError) as error:
        print("learner view: FAIL: " + str(error), file=sys.stderr)
        sys.exit(1)
