"""Deterministic archive-safety and metadata checks for this challenge pack."""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

REQUIRED = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "VALIDATION.md",
    "starter/README.md",
    "public_tests/README.md",
    "environment/README.md",
    "sealed/reference/README.md",
    "sealed/reference_tests/README.md",
    "sealed/DESIGN.md",
    "sealed/TRADEOFFS.md",
    "sealed/REVIEW.md",
    "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md",
    "adversarial/README.md",
    "debugging/README.md",
    "review_exercises/README.md",
    "benchmarks/README.md",
)

FORBIDDEN = (
    ".git",
    ".env",
    ".venv",
    "credentials.json",
    "secrets",
    "reference",
    "reference_tests",
    "hidden_tests",
    "solution",
    "solutions",
    "answers",
    "starter/sealed",
    "starter/reference",
    "starter/reference_tests",
    "starter/solution",
    "starter/solutions",
    "starter/answers",
    "public_tests/sealed",
    "public_tests/reference",
    "public_tests/hidden_tests",
    "environment/sealed",
)

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_ce9cae8ab2c9c820ceec425c2639e501",
    "provenance_sha256":
        "7cedc44e4fb22194236a8939bd566c5734dfdb3d379f192ed8c7ce1e7159ef6a",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"ghp_[A-Za-z0-9]{30,}"),
    re.compile(rb"sk-[A-Za-z0-9]{32,}"),
)

# Workspace-control directories are owned by the harness, not generated pack
# material. Do not descend into or archive-scan them.
CONTROL_DIRECTORIES = {".agents", ".codex", ".factory-workspace"}


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing required regular file: {relative}")

    for relative in FORBIDDEN:
        path = ROOT / relative
        if path.exists() or path.is_symlink():
            errors.append(f"forbidden path exists: {relative}")

    for current, directory_names, file_names in os.walk(ROOT, followlinks=False):
        current_path = Path(current)
        if current_path == ROOT:
            directory_names[:] = [
                name for name in directory_names
                if name not in CONTROL_DIRECTORIES
            ]
        for name in directory_names + file_names:
            path = current_path / name
            relative = path.relative_to(ROOT).as_posix()
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                errors.append(f"symbolic link is not archivable: {relative}")
            elif not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                errors.append(f"special filesystem object: {relative}")
            elif stat.S_ISREG(mode):
                content = path.read_bytes()
                for pattern in SECRET_PATTERNS:
                    if pattern.search(content):
                        errors.append(f"credential-like material in: {relative}")
                        break

    try:
        manifest = json.loads((ROOT / "MANIFEST.yaml").read_text("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        errors.append(f"MANIFEST.yaml is not strict JSON: {error}")
    else:
        if manifest != EXPECTED_MANIFEST:
            errors.append("MANIFEST.yaml does not equal the required object")

    try:
        provenance = json.loads((ROOT / "PROVENANCE.json").read_text("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        errors.append(f"PROVENANCE.json is not strict JSON: {error}")
    else:
        if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
            errors.append("provenance snapshot does not match the manifest")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"structure: PASS ({len(REQUIRED)} required files, no forbidden paths)")
    print("archive types: PASS (regular files and directories only)")
    print("credential patterns: PASS")
    print("metadata status: PASS (GENERATED + PARTIAL)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
