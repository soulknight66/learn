#!/usr/bin/env python3
"""Deterministic structural and metadata audit for this generated pack."""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import stat
import sys


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
    "project_id": "project_a39dec7bd5caf7524c0e9df3e14a2c8b",
    "provenance_sha256": "0ecf54a73c5abbc7f8076dcea9d02c6e201b04eb9ba65afba16b51915648ecd2",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

EXPECTED_PROVENANCE_CANONICAL_SHA256 = (
    "1bfdb2c3fd69ba8b002ae897ba75fc03684b636e83ee1541aaefb3eeaff8ce7e"
)

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|secret|password)\s*[:=]\s*"
        r"[\"'][^\"'\r\n]{8,}[\"']"
    ),
)


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def fail(messages: list[str], message: str) -> None:
    messages.append(message)


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    problems: list[str] = []

    for relative in REQUIRED:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            fail(problems, f"required regular file missing: {relative}")

    for relative in FORBIDDEN:
        if (root / relative).exists() or (root / relative).is_symlink():
            fail(problems, f"forbidden path exists: {relative}")

    for path in root.rglob("*"):
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            fail(problems, f"non-regular filesystem object: {path.relative_to(root)}")

    try:
        manifest = json.loads((root / "MANIFEST.yaml").read_text(encoding="utf-8"))
        provenance = json.loads((root / "PROVENANCE.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(problems, f"metadata parse failed: {error}")
    else:
        if manifest != EXPECTED_MANIFEST:
            fail(problems, "manifest object differs from immutable expectation")
        provenance_hash = canonical_sha256(provenance)
        if provenance_hash != EXPECTED_PROVENANCE_CANONICAL_SHA256:
            fail(problems, "provenance object differs from immutable expectation")

    scanned = 0
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if not path.is_file() or relative.parts[0].startswith("."):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                fail(problems, f"credential-like content in {relative}")
                break

    if problems:
        for problem in problems:
            print(f"AUDIT FAILURE: {problem}", file=sys.stderr)
        return 1
    print(
        f"pack audit: PASS ({len(REQUIRED)} required files, "
        f"{len(FORBIDDEN)} forbidden paths absent, {scanned} text files scanned)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
