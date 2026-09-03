#!/usr/bin/env python3
"""Deterministic packaging audit over generated, allowlisted paths only."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
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
]
FORBIDDEN = [
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
]
GENERATED_ROOTS = [
    "starter",
    "public_tests",
    "environment",
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
]
TOP_LEVEL_FILES = [
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "VALIDATION.md",
]
ASSIGNMENT = re.compile(
    rb"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|"
    rb"password|passwd|private[_-]?key)\b\s*[:=]\s*['\"]?[A-Za-z0-9_/+.-]{8,}"
)
PEM_HEADER = re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
BASIC_AUTH_URL = re.compile(rb"https?://[^/\s:@]+:[^@\s/]+@")
PROVENANCE_FILE_SHA256 = (
    "8aa702b8b64241bda70f3a63e3d1b9a681e7dc87f4d5930b9b4f764f584e5dad"
)


def fail(message):
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def generated_paths():
    for relative in TOP_LEVEL_FILES:
        yield ROOT / relative
    for relative in GENERATED_ROOTS:
        base = ROOT / relative
        if not base.exists():
            continue
        for directory, names, files in os.walk(base, followlinks=False):
            directory_path = Path(directory)
            for name in names:
                yield directory_path / name
            for name in files:
                yield directory_path / name


def main():
    errors = 0
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        errors += fail(f"missing required regular files: {missing}")

    present_forbidden = [path for path in FORBIDDEN if (ROOT / path).exists()]
    if present_forbidden:
        errors += fail(f"forbidden paths present: {present_forbidden}")

    files = []
    seen = set()
    for path in generated_paths():
        if path in seen:
            continue
        seen.add(path)
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            errors += fail(f"non-regular generated entry: {path.relative_to(ROOT)}")
            continue
        files.append(path)

    credential_hits = []
    for path in files:
        data = path.read_bytes()
        if ASSIGNMENT.search(data) or PEM_HEADER.search(data) or BASIC_AUTH_URL.search(data):
            credential_hits.append(str(path.relative_to(ROOT)))
    if credential_hits:
        errors += fail(f"credential-like material found: {credential_hits}")

    try:
        manifest = json.loads((ROOT / "MANIFEST.yaml").read_text())
        provenance_bytes = (ROOT / "PROVENANCE.json").read_bytes()
        provenance = json.loads(provenance_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        errors += fail(f"strict JSON parse failed: {error}")
    else:
        expected_manifest = {
            "independent_validation": "REQUIRED",
            "productionized": False,
            "project_id": "project_88e5a9a922f8f9e2166223c1333f28f9",
            "provenance_sha256": "5cf87366deb474541c8f241298378a98ea45ed8e1148a6e687a8102a74b0df63",
            "schema_version": 1,
            "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
            "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
            "status": "GENERATED",
            "validation_labels": ["GENERATED", "PARTIAL"],
        }
        if manifest != expected_manifest:
            errors += fail("MANIFEST.yaml differs from its authoritative object")
        if hashlib.sha256(provenance_bytes).hexdigest() != PROVENANCE_FILE_SHA256:
            errors += fail("PROVENANCE.json byte digest differs from pinned SHA-256")
        if provenance.get("snapshot_sha256") != manifest.get("provenance_sha256"):
            errors += fail("source-snapshot identifier differs across metadata files")
        if provenance.get("project", {}).get("project_id") != manifest.get("project_id"):
            errors += fail("project identity differs across metadata files")

    if errors:
        return 1
    print(f"required files: {len(REQUIRED)} present")
    print("forbidden paths: 0 present")
    print(f"generated entries audited: {len(seen)}")
    print(f"regular files scanned for credential patterns: {len(files)}")
    print("metadata: strict JSON; manifest object exact; source snapshot consistent")
    print("provenance document: pinned file SHA-256 verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
