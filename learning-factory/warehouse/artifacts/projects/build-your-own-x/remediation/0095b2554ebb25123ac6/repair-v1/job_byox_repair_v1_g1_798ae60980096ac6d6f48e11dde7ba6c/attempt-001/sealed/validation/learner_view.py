#!/usr/bin/env python3
"""Materialize and verify the machine-readable learner view."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys


POLICY_PATH = Path("environment/learner-view.json")
EXPECTED_ALLOWED = (
    ("README.md", "file", "read-only"),
    ("AGENTS.md", "file", "read-only"),
    ("MANIFEST.yaml", "file", "read-only"),
    ("REQUIREMENTS.md", "file", "read-only"),
    ("CONCEPTS.md", "file", "read-only"),
    ("DESIGN_QUESTIONS.md", "file", "read-only"),
    ("starter", "directory", "read-write"),
    ("public_tests", "directory", "read-only"),
    ("environment", "directory", "read-only"),
)
EXPECTED_DENIED = (
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "VALIDATION.md",
)


class ViewError(Exception):
    pass


def load_policy(source_root):
    policy_file = source_root / POLICY_PATH
    try:
        policy = json.loads(policy_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ViewError("cannot read learner-view policy: {}".format(error))
    expected_keys = {"schema_version", "allowed_entries", "denied_prefixes", "runtime_boundary"}
    if set(policy) != expected_keys or policy["schema_version"] != 1:
        raise ViewError("learner-view policy has an unsupported schema")
    allowed = tuple(
        (item.get("path"), item.get("kind"), item.get("access"))
        for item in policy["allowed_entries"]
        if isinstance(item, dict)
    )
    if allowed != EXPECTED_ALLOWED or len(allowed) != len(policy["allowed_entries"]):
        raise ViewError("learner-view allowlist differs from the fixed contract")
    if tuple(policy["denied_prefixes"]) != EXPECTED_DENIED:
        raise ViewError("learner-view deny list differs from the fixed contract")
    if policy["runtime_boundary"] != {
        "learner_mount": "/workspace",
        "source_pack_mounted": False,
    }:
        raise ViewError("learner-view runtime boundary differs from the fixed contract")
    return policy


def _entry_kind(path):
    mode = path.lstat().st_mode
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "directory"
    raise ViewError("special entry is not allowed: {}".format(path))


def _copy_entry(source, destination, writable):
    kind = _entry_kind(source)
    if kind == "file":
        destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        shutil.copyfile(str(source), str(destination))
        destination.chmod(0o644 if writable else 0o444)
        return
    destination.mkdir(mode=0o755, parents=True, exist_ok=False)
    for child in sorted(source.iterdir(), key=lambda path: path.name):
        _copy_entry(child, destination / child.name, writable)
    destination.chmod(0o755 if writable else 0o555)


def _remove_created_tree(path):
    if not os.path.lexists(str(path)):
        return
    for directory, directories, filenames in os.walk(str(path), topdown=False, followlinks=False):
        base = Path(directory)
        for name in directories:
            child = base / name
            if not child.is_symlink():
                child.chmod(0o700)
        base.chmod(0o700)
    shutil.rmtree(str(path))


def verify_view(view_root):
    policy = load_policy(view_root)
    expected_names = {item[0] for item in EXPECTED_ALLOWED}
    actual_names = {path.name for path in view_root.iterdir()}
    if actual_names != expected_names:
        raise ViewError("view top level is {}, expected {}".format(sorted(actual_names), sorted(expected_names)))
    for relative, expected_kind, unused_access in EXPECTED_ALLOWED:
        path = view_root / relative
        if _entry_kind(path) != expected_kind:
            raise ViewError("wrong entry kind for {}".format(relative))
    for relative, unused_kind, access in EXPECTED_ALLOWED:
        top = view_root / relative
        paths = [top]
        if top.is_dir():
            for directory, directories, filenames in os.walk(str(top), followlinks=False):
                base = Path(directory)
                paths.extend(base / name for name in directories + filenames)
        for path in paths:
            mode = stat.S_IMODE(path.lstat().st_mode)
            expected_mode = 0o755 if path.is_dir() else 0o644
            if access == "read-only":
                expected_mode = 0o555 if path.is_dir() else 0o444
            if mode != expected_mode:
                raise ViewError("wrong access mode for {}: {:o}".format(path.relative_to(view_root), mode))
    for relative in policy["denied_prefixes"]:
        if os.path.lexists(str(view_root / relative)):
            raise ViewError("denied path is present: {}".format(relative))
    for directory, directories, filenames in os.walk(str(view_root), followlinks=False):
        base = Path(directory)
        for name in directories + filenames:
            _entry_kind(base / name)
    return content_digest(view_root)


def content_digest(root):
    digest = hashlib.sha256()
    digest.update(b"learner-view-v1\0")
    files = []
    for directory, unused_directories, filenames in os.walk(str(root), followlinks=False):
        base = Path(directory)
        files.extend(base / name for name in filenames)
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(str(len(relative)).encode("ascii") + b":" + relative)
        digest.update(str(len(data)).encode("ascii") + b":" + data)
    return digest.hexdigest()


def materialize(source_root, destination):
    source_root = source_root.resolve(strict=True)
    policy = load_policy(source_root)
    destination = destination.parent.resolve(strict=True) / destination.name
    if destination == source_root or source_root in destination.parents:
        raise ViewError("destination must be outside the source pack")
    if os.path.lexists(str(destination)):
        raise ViewError("destination already exists")
    destination.mkdir(mode=0o700)
    try:
        for relative, expected_kind, access in EXPECTED_ALLOWED:
            source = source_root / relative
            if _entry_kind(source) != expected_kind:
                raise ViewError("source entry kind is wrong: {}".format(relative))
            _copy_entry(source, destination / relative, access == "read-write")
        digest = verify_view(destination)
    except Exception:
        _remove_created_tree(destination)
        raise
    return {"content_sha256": digest, "policy": policy}


def main(argv):
    if not argv or argv[0] not in ("build", "verify") or (argv[0] == "build" and len(argv) != 3) or (argv[0] == "verify" and len(argv) != 2):
        print("usage: learner_view.py build SOURCE DEST | verify VIEW", file=sys.stderr)
        return 2
    try:
        if argv[0] == "build":
            result = materialize(Path(argv[1]), Path(argv[2]))
            print("PASS learner view built: {}".format(result["content_sha256"]))
        else:
            print("PASS learner view verified: {}".format(verify_view(Path(argv[1]).resolve(strict=True))))
    except (OSError, ViewError) as error:
        print("FAIL {}".format(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
