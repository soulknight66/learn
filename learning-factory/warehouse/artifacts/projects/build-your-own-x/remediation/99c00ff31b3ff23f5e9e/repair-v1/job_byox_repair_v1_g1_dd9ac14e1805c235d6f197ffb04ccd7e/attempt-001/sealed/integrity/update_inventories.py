#!/usr/bin/env python3
"""Regenerate deterministic student-view and full-pack content inventories."""

import hashlib
import json
import os
from pathlib import Path
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]
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
ARTIFACT_ROOT_FILES = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "VALIDATION.md",
)
ARTIFACT_DIRECTORIES = (
    "starter",
    "public_tests",
    "environment",
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
)
STUDENT_INVENTORY = "environment/STUDENT_VIEW_INVENTORY.json"
ARTIFACT_INVENTORY = "sealed/ARTIFACT_INVENTORY.json"


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(65536)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def collect(roots, excluded):
    found = {}
    for relative_text in roots:
        path = ROOT / relative_text
        if not path.exists() or path.is_symlink():
            raise ValueError("missing or symbolic inventory root: {}".format(relative_text))
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            if relative_text not in excluded:
                found[relative_text] = path
            continue
        if not stat.S_ISDIR(mode):
            raise ValueError("special inventory root: {}".format(relative_text))
        for current, directories, files in os.walk(str(path), followlinks=False):
            directories.sort()
            files.sort()
            current_path = Path(current)
            for name in directories:
                child = current_path / name
                if child.is_symlink() or not stat.S_ISDIR(child.lstat().st_mode):
                    raise ValueError(
                        "symbolic or special path: {}".format(child.relative_to(ROOT))
                    )
            for name in files:
                child = current_path / name
                relative = str(child.relative_to(ROOT))
                if child.is_symlink() or not stat.S_ISREG(child.lstat().st_mode):
                    raise ValueError("symbolic or special path: {}".format(relative))
                if relative not in excluded:
                    found[relative] = child
    return found


def entries(files):
    return [
        {
            "path": relative,
            "sha256": sha256_file(files[relative]),
            "size": files[relative].stat().st_size,
            "type": "regular-file",
        }
        for relative in sorted(files)
    ]


def write_inventory(relative, scope, excluded, files):
    document = {
        "algorithm": "sha256",
        "excluded_from_hashes": list(excluded),
        "files": entries(files),
        "schema_version": 1,
        "scope": scope,
    }
    destination = ROOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main():
    try:
        student_files = collect(VISIBLE_ROOTS, {STUDENT_INVENTORY})
        write_inventory(
            STUDENT_INVENTORY,
            "exact learner-visible projection",
            (STUDENT_INVENTORY,),
            student_files,
        )
        artifact_roots = ARTIFACT_ROOT_FILES + ARTIFACT_DIRECTORIES
        artifact_files = collect(artifact_roots, {ARTIFACT_INVENTORY})
        write_inventory(
            ARTIFACT_INVENTORY,
            "complete challenge pack except this self-referential inventory",
            (ARTIFACT_INVENTORY,),
            artifact_files,
        )
    except (OSError, ValueError) as error:
        print("FAIL: {}".format(error), file=sys.stderr)
        return 1
    print("student-view-inventory: {} hashed regular files".format(len(student_files)))
    print("artifact-inventory: {} hashed regular files".format(len(artifact_files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
