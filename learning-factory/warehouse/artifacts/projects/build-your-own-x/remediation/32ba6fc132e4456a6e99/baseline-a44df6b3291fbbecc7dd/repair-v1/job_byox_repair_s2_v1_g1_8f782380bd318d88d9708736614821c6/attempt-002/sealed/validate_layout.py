#!/usr/bin/env python3
"""Deterministic packaging and secret-pattern checks for this artifact."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import stat


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

GENERATED_TOP_LEVEL = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "VALIDATION.md",
    "starter",
    "public_tests",
    "environment",
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
)

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_7fc5b6faee61f34679ec47f9c4964256",
    "provenance_sha256": "3eb25de5bc0119c56a4a71be4ea9b969116635a2bbf54acfbc5cae7e5da59c87",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

SECRET_PATTERNS = {
    "PEM private key": re.compile(rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{36,255}"),
    "OpenAI-style key": re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    "assigned credential": re.compile(
        rb"(?i)(?:password|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*[\"'][^\"'\r\n]{8,}"
    ),
}


def generated_paths(root: Path) -> list[Path]:
    result: list[Path] = []
    for name in GENERATED_TOP_LEVEL:
        start = root / name
        if not start.exists() and not start.is_symlink():
            continue
        if start.is_dir() and not start.is_symlink():
            result.append(start)
            result.extend(sorted(start.rglob("*")))
        else:
            result.append(start)
    return result


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    problems: list[str] = []

    for relative in REQUIRED:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            problems.append(f"required regular file missing: {relative}")
    for relative in FORBIDDEN:
        path = root / relative
        if path.exists() or path.is_symlink():
            problems.append(f"forbidden path exists: {relative}")

    paths = generated_paths(root)
    files: list[Path] = []
    for path in paths:
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            files.append(path)
        elif not stat.S_ISDIR(mode):
            problems.append(f"non-regular generated path: {path.relative_to(root)}")

    try:
        manifest = json.loads((root / "MANIFEST.yaml").read_text(encoding="utf-8"))
        provenance = json.loads((root / "PROVENANCE.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as failure:
        problems.append(f"strict JSON parsing failed: {failure}")
    else:
        if manifest != EXPECTED_MANIFEST:
            problems.append("MANIFEST.yaml does not equal the authoritative object")
        if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
            problems.append("PROVENANCE.json snapshot hash does not match manifest")
        if provenance.get("project", {}).get("project_id") != EXPECTED_MANIFEST["project_id"]:
            problems.append("PROVENANCE.json project ID does not match manifest")

    for path in files:
        try:
            content = path.read_bytes()
        except OSError as failure:
            problems.append(f"cannot scan {path.relative_to(root)}: {failure}")
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                problems.append(f"{label} pattern in {path.relative_to(root)}")

    if problems:
        for problem in problems:
            print("FAIL " + problem)
        return 1

    manifest_hash = hashlib.sha256((root / "MANIFEST.yaml").read_bytes()).hexdigest()
    provenance_hash = hashlib.sha256((root / "PROVENANCE.json").read_bytes()).hexdigest()
    print(f"PASS required regular files: {len(REQUIRED)}")
    print(f"PASS forbidden paths absent: {len(FORBIDDEN)}")
    print(f"PASS generated paths are regular files/directories: {len(paths)} paths")
    print(f"PASS strict JSON and GENERATED+PARTIAL manifest: {manifest_hash}")
    print(f"PASS provenance linkage and strict JSON: {provenance_hash}")
    print(f"PASS credential-pattern scan: {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
