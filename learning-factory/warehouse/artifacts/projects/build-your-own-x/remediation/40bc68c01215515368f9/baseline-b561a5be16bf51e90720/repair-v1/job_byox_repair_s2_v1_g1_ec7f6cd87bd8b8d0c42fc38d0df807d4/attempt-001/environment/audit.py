#!/usr/bin/env python3
"""Deterministic packaging audit; uses only the Python standard library."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat


ROOT = Path(__file__).resolve().parent.parent

REQUIRED = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json", "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md", "CONCEPTS.md", "DESIGN_QUESTIONS.md", "VALIDATION.md",
    "starter/README.md", "public_tests/README.md", "environment/README.md",
    "sealed/reference/README.md", "sealed/reference_tests/README.md", "sealed/DESIGN.md",
    "sealed/TRADEOFFS.md", "sealed/REVIEW.md", "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md", "adversarial/README.md", "debugging/README.md",
    "review_exercises/README.md", "benchmarks/README.md",
]

FORBIDDEN = [
    ".git", ".env", ".venv", "credentials.json", "secrets", "reference", "reference_tests",
    "hidden_tests", "solution", "solutions", "answers", "starter/sealed", "starter/reference",
    "starter/reference_tests", "starter/solution", "starter/solutions", "starter/answers",
    "public_tests/sealed", "public_tests/reference", "public_tests/hidden_tests", "environment/sealed",
]

GENERATED_ROOTS = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json", "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md", "CONCEPTS.md", "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter",
    "public_tests", "environment", "sealed", "adversarial", "debugging", "review_exercises",
    "benchmarks",
]

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_d87a4b192af7a71c0932b920abc8cad6",
    "provenance_sha256": "3d238e481462341641362800952c5e683439b805ac30f55f9888de705ac8df5a",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

CREDENTIAL_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "OpenAI-style key": re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    "bearer credential": re.compile(rb"Bearer[ \t]+[A-Za-z0-9._~-]{20,}"),
}


def fail(message: str) -> None:
    raise SystemExit("AUDIT FAIL: " + message)


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        fail(f"missing required regular files: {missing}")

    forbidden = [name for name in FORBIDDEN if os.path.lexists(ROOT / name)]
    if forbidden:
        fail(f"forbidden paths exist: {forbidden}")

    manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
    if manifest != EXPECTED_MANIFEST:
        fail("MANIFEST.yaml differs from its authoritative object")

    provenance = json.loads((ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
    if provenance.get("snapshot_sha256") != manifest["provenance_sha256"]:
        fail("provenance snapshot hash does not match manifest")
    if provenance.get("project", {}).get("project_id") != manifest["project_id"]:
        fail("provenance project id does not match manifest")
    if provenance.get("source", {}).get("source_id") != manifest["source_id"]:
        fail("provenance source id does not match manifest")
    boundary = provenance.get("license_boundary", {})
    if boundary.get("linked_content_copied") is not False or boundary.get("linked_resource_license") != "NOASSERTION":
        fail("license boundary is not the expected no-copy/NOASSERTION boundary")

    files: list[Path] = []
    for root_name in GENERATED_ROOTS:
        root = ROOT / root_name
        paths = [root] if not root.is_dir() else [root, *root.rglob("*")]
        for path in paths:
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                fail(f"generated symlink: {path.relative_to(ROOT)}")
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                fail(f"generated special path: {path.relative_to(ROOT)}")
            if stat.S_ISREG(mode):
                files.append(path)

    hits: list[str] = []
    for path in files:
        data = path.read_bytes()
        for label, pattern in CREDENTIAL_PATTERNS.items():
            if pattern.search(data):
                hits.append(f"{path.relative_to(ROOT)} ({label})")
    if hits:
        fail(f"credential-like signatures found: {hits}")

    print(f"required regular files: PASS ({len(REQUIRED)}/{len(REQUIRED)})")
    print(f"forbidden paths absent: PASS ({len(FORBIDDEN)}/{len(FORBIDDEN)})")
    print("manifest exact object and provenance linkage: PASS")
    print(f"generated path types: PASS ({len(files)} regular files; no symlinks/special files)")
    print(f"credential signature scan: PASS ({len(files)} files, {len(CREDENTIAL_PATTERNS)} patterns, 0 hits)")


if __name__ == "__main__":
    main()
