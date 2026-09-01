#!/usr/bin/env python3
"""Verify the structure, hashes, and hygiene of a projected student view."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


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
INVENTORY_RELATIVE = "environment/STUDENT_VIEW_INVENTORY.json"
BAD_NAMES = {
    ".git",
    ".env",
    ".venv",
    "credentials.json",
    "secrets",
    "sealed",
    "reference",
    "reference_tests",
    "hidden_tests",
    "solution",
    "solutions",
    "answers",
}
EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_bd342fcec50cb8a15740cbb98e57bc1e",
    "provenance_sha256": "16c1f2fa7154cfbf9531c6d77cf7024fd08511e5def5b6488d364f550056629b",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}
PATTERNS = (
    re.compile(br"AKIA[0-9A-Z]{16}"),
    re.compile(br"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(br"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(br"sk-[A-Za-z0-9]{20,}"),
    re.compile(br"(?:password|passwd)\s*=\s*[^\s]+", re.IGNORECASE),
)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(65536)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def walk_view(root):
    regular = {}
    unusual = []
    for current, directories, files in os.walk(str(root), followlinks=False):
        directories.sort()
        files.sort()
        current_path = Path(current)
        for name in directories + files:
            path = current_path / name
            relative = str(path.relative_to(root))
            mode = path.lstat().st_mode
            if stat.S_ISREG(mode) and not path.is_symlink():
                regular[relative] = path
            elif not stat.S_ISDIR(mode) or path.is_symlink():
                unusual.append(relative)
    return regular, unusual


def verify(root):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        print("FAIL: student-view root is not a regular directory")
        return 1

    actual_top = sorted(path.name for path in root.iterdir())
    expected_top = sorted(VISIBLE_ROOTS)
    if actual_top != expected_top:
        print("FAIL: student-view top level differs from the exact allowlist")
        return 1
    print("student-view-top-level: 9/9 allowlisted entries only")

    regular, unusual = walk_view(root)
    if unusual:
        print("FAIL: student-view symlinks or special paths: {}".format(", ".join(unusual)))
        return 1
    print("student-view-symlinks-or-special-files: 0")

    forbidden = []
    for relative in regular:
        if any(part in BAD_NAMES for part in Path(relative).parts):
            forbidden.append(relative)
    if forbidden:
        print("FAIL: forbidden student-view paths: {}".format(", ".join(forbidden)))
        return 1
    print("student-view-forbidden-paths: 0")

    inventory_path = root / INVENTORY_RELATIVE
    try:
        with inventory_path.open("r", encoding="utf-8") as handle:
            inventory = json.load(handle)
    except (OSError, ValueError) as error:
        print("FAIL: cannot load student-view inventory: {}".format(error))
        return 1
    expected_keys = {
        "algorithm", "excluded_from_hashes", "files", "schema_version", "scope"
    }
    if (
        set(inventory) != expected_keys
        or inventory.get("algorithm") != "sha256"
        or inventory.get("excluded_from_hashes") != [INVENTORY_RELATIVE]
        or inventory.get("schema_version") != 1
        or inventory.get("scope") != "exact learner-visible projection"
        or not isinstance(inventory.get("files"), list)
    ):
        print("FAIL: malformed student-view inventory metadata")
        return 1

    entries = inventory["files"]
    entry_paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
    actual_hashed = sorted(path for path in regular if path != INVENTORY_RELATIVE)
    if (
        len(entry_paths) != len(entries)
        or entry_paths != sorted(entry_paths)
        or entry_paths != actual_hashed
    ):
        print("FAIL: student-view inventory path set differs from materialized files")
        return 1
    for entry in entries:
        if set(entry) != {"path", "sha256", "size", "type"}:
            print("FAIL: malformed inventory entry for {}".format(entry.get("path")))
            return 1
        path = regular[entry["path"]]
        if (
            entry["type"] != "regular-file"
            or entry["size"] != path.stat().st_size
            or entry["sha256"] != sha256_file(path)
        ):
            print("FAIL: student-view content mismatch: {}".format(entry["path"]))
            return 1
    print(
        "student-view-content-inventory: {0}/{0} regular files match sha256".format(
            len(entries)
        )
    )

    try:
        with (root / "MANIFEST.yaml").open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError) as error:
        print("FAIL: cannot load manifest: {}".format(error))
        return 1
    if manifest != EXPECTED_MANIFEST:
        print("FAIL: projected manifest differs from the immutable expected object")
        return 1
    print("student-view-manifest: exact GENERATED + PARTIAL object")

    matches = []
    for relative, path in sorted(regular.items()):
        content = path.read_bytes()
        if any(pattern.search(content) for pattern in PATTERNS):
            matches.append(relative)
    if matches:
        print("FAIL: student-view credential-shaped content: {}".format(", ".join(matches)))
        return 1
    print("student-view-credential-pattern-scan: no matches")
    return 0


def main():
    if len(sys.argv) > 2:
        print("usage: verify_student_view.py [VIEW]", file=sys.stderr)
        return 2
    if len(sys.argv) == 2:
        root = Path(sys.argv[1])
    else:
        root = Path(__file__).resolve().parents[1]
    return verify(root)


if __name__ == "__main__":
    sys.exit(main())
