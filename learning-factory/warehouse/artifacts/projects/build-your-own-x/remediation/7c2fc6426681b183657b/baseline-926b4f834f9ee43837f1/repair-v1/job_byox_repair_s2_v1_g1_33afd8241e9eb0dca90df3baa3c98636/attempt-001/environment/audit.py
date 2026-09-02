#!/usr/bin/env python3
"""Deterministic structure, boundary, JSON, and credential-pattern audit."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]

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
    "starter/Makefile",
    "starter/forth.S",
    "public_tests/README.md",
    "public_tests/test_cinder.py",
    "environment/README.md",
    "environment/audit.py",
    "environment/build.py",
    "environment/test_tooling.py",
    "sealed/reference/README.md",
    "sealed/reference/forth.S",
    "sealed/reference_tests/README.md",
    "sealed/reference_tests/DEVELOPMENT_LOG.md",
    "sealed/reference_tests/test_reference.py",
    "sealed/DESIGN.md",
    "sealed/TRADEOFFS.md",
    "sealed/REVIEW.md",
    "sealed/alternatives/README.md",
    "sealed/debugging/01-stack/sealed/ANSWER.md",
    "sealed/debugging/02-control-flow/sealed/ANSWER.md",
    "sealed/production/PRODUCTIONIZATION.md",
    "sealed/review_exercises/01-division/sealed/ANSWER.md",
    "sealed/review_exercises/02-parser/sealed/ANSWER.md",
    "adversarial/README.md",
    "debugging/README.md",
    "review_exercises/README.md",
    "benchmarks/README.md",
    "benchmarks/run.py",
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
    "project_id": "project_d667887dddd98fbea55fa17d9b99cf19",
    "provenance_sha256": "5b3c54fa4b6a8eee00ab5c77a2bafa9a0762f55f2ddf9656ccee2386cee990b0",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

# SHA-256 of the canonical encoding produced by json.dumps with sorted keys and
# compact separators. This binds every provenance field and is deliberately
# distinct from EXPECTED_MANIFEST["provenance_sha256"], which is the immutable
# source-snapshot identifier carried inside PROVENANCE.json.
EXPECTED_PROVENANCE_OBJECT_SHA256 = "dc759cd6068016565adafc56a86680e216fda2867ba90aed0c352f07ff2a6017"

CREDENTIAL_PATTERNS = (
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        rb"(?i)(?:api[_-]?key|password|passwd|client[_-]?secret|access[_-]?token)"
        rb"\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]"
    ),
    re.compile(rb"gh[pousr]_[A-Za-z0-9_]{30,}"),
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def validate_metadata(root: Path) -> None:
    manifest = json.loads((root / "MANIFEST.yaml").read_text(encoding="utf-8"))
    if manifest != EXPECTED_MANIFEST:
        fail("MANIFEST.yaml differs from the authoritative object")

    provenance = json.loads((root / "PROVENANCE.json").read_text(encoding="utf-8"))
    canonical_provenance = json.dumps(
        provenance, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    provenance_object_sha256 = hashlib.sha256(canonical_provenance).hexdigest()
    if provenance_object_sha256 != EXPECTED_PROVENANCE_OBJECT_SHA256:
        fail("PROVENANCE.json differs from the authoritative complete object")
    if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
        fail("provenance source-snapshot identifier does not match manifest")
    if provenance.get("project", {}).get("project_id") != EXPECTED_MANIFEST["project_id"]:
        fail("provenance project id does not match manifest")


def audit_pack(root: Path) -> dict[str, int | bool]:
    for relative in REQUIRED:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            fail(f"missing regular required file: {relative}")

    for relative in FORBIDDEN:
        if (root / relative).exists() or (root / relative).is_symlink():
            fail(f"forbidden path exists: {relative}")

    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        for name in directory_names + file_names:
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                fail(f"non-regular archive entry: {path.relative_to(root)}")

    validate_metadata(root)

    scan_roots = [
        root / name
        for name in (
            "README.md",
            "AGENTS.md",
            "LICENSE_BOUNDARY.md",
            "REQUIREMENTS.md",
            "CONCEPTS.md",
            "DESIGN_QUESTIONS.md",
            "VALIDATION.md",
            "MANIFEST.yaml",
            "PROVENANCE.json",
            "starter",
            "public_tests",
            "environment",
            "sealed",
            "adversarial",
            "debugging",
            "review_exercises",
            "benchmarks",
        )
    ]
    scanned = 0
    for root in scan_roots:
        paths = [root] if root.is_file() else sorted(path for path in root.rglob("*") if path.is_file())
        for path in paths:
            if path.suffix in {".pyc"} or "build" in path.parts:
                continue
            payload = path.read_bytes()
            scanned += 1
            for pattern in CREDENTIAL_PATTERNS:
                if pattern.search(payload):
                    fail(f"credential-like pattern in {path.relative_to(root)}")

    return {
        "credential_patterns": len(CREDENTIAL_PATTERNS),
        "files_scanned": scanned,
        "forbidden_absent": len(FORBIDDEN),
        "manifest_exact": True,
        "provenance_object_exact": True,
        "required_regular": len(REQUIRED),
        "special_entries_absent": True,
    }


def main() -> int:
    print(json.dumps(audit_pack(ROOT), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, UnicodeError, json.JSONDecodeError) as error:
        sys.stderr.write(f"audit failed: {error}\n")
        raise SystemExit(1)
