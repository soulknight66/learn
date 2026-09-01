#!/usr/bin/env python3
"""Deterministic structure and leakage audit for this challenge pack."""

import hashlib
import json
import re
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

REQUIRED = {
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
}

FORBIDDEN = {
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
}

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_1f6075dda621ad56c06108ef7c87e871",
    "provenance_sha256": "8b6a7a8c0f0f92d20fe4c3540d07d2ad305b8e3195524e906288fb2523d8dcde",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

PROVENANCE_CANONICAL_SHA256 = (
    "391975dbe42ec58e9deca907dab0f42477c57f4e331ded66f3c7da66e1d578ca"
)

CREDENTIAL_PATTERNS = {
    "private key block": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
    "OpenAI-style secret": re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    "assigned credential": re.compile(
        rb"(?i)(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*[\"'][^\"']+[\"']"
    ),
}


def canonical_sha256(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    errors = []

    for relative in sorted(REQUIRED):
        if not (ROOT / relative).is_file():
            errors.append(f"missing required regular file: {relative}")
    for relative in sorted(FORBIDDEN):
        if (ROOT / relative).exists():
            errors.append(f"forbidden path exists: {relative}")

    for path in ROOT.rglob("*"):
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            errors.append(f"non-regular/non-directory path: {path.relative_to(ROOT)}")

    try:
        manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
        if manifest != EXPECTED_MANIFEST:
            errors.append("MANIFEST.yaml differs from its authoritative object")
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        errors.append(f"MANIFEST.yaml is not strict JSON: {error}")

    try:
        provenance = json.loads((ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
        if canonical_sha256(provenance) != PROVENANCE_CANONICAL_SHA256:
            errors.append("PROVENANCE.json differs from its authoritative snapshot")
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        errors.append(f"PROVENANCE.json is not strict JSON: {error}")

    ignored_factory_files = {ROOT / "JOB.md", ROOT / ".factory-workspace"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path in ignored_factory_files:
            continue
        data = path.read_bytes()
        for label, pattern in CREDENTIAL_PATTERNS.items():
            if pattern.search(data):
                errors.append(f"possible {label} in {path.relative_to(ROOT)}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        raise SystemExit(1)
    print(f"PASS: {len(REQUIRED)} required files are regular files")
    print(f"PASS: {len(FORBIDDEN)} forbidden paths are absent")
    print("PASS: manifest and provenance match their authoritative JSON values")
    print("PASS: no symlinks, special files, or recognized credential material found")


if __name__ == "__main__":
    main()
