#!/usr/bin/env python3
"""Deterministic structure, boundary, JSON, and credential-pattern audit."""

from __future__ import annotations

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
    "project_id": "project_d667887dddd98fbea55fa17d9b99cf19",
    "provenance_sha256": "5b3c54fa4b6a8eee00ab5c77a2bafa9a0762f55f2ddf9656ccee2386cee990b0",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

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


def main() -> int:
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            fail(f"missing regular required file: {relative}")

    for relative in FORBIDDEN:
        if (ROOT / relative).exists() or (ROOT / relative).is_symlink():
            fail(f"forbidden path exists: {relative}")

    for directory, directory_names, file_names in os.walk(ROOT, followlinks=False):
        for name in directory_names + file_names:
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                fail(f"non-regular archive entry: {path.relative_to(ROOT)}")

    manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
    if manifest != EXPECTED_MANIFEST:
        fail("MANIFEST.yaml differs from the authoritative object")
    provenance = json.loads((ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
    if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
        fail("provenance snapshot hash does not match manifest binding")
    if provenance.get("project", {}).get("project_id") != EXPECTED_MANIFEST["project_id"]:
        fail("provenance project id does not match manifest")

    scan_roots = [
        ROOT / name
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
                    fail(f"credential-like pattern in {path.relative_to(ROOT)}")

    print(
        json.dumps(
            {
                "credential_patterns": len(CREDENTIAL_PATTERNS),
                "files_scanned": scanned,
                "forbidden_absent": len(FORBIDDEN),
                "manifest_exact": True,
                "provenance_binding": True,
                "required_regular": len(REQUIRED),
                "special_entries_absent": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, UnicodeError, json.JSONDecodeError) as error:
        sys.stderr.write(f"audit failed: {error}\n")
        raise SystemExit(1)
