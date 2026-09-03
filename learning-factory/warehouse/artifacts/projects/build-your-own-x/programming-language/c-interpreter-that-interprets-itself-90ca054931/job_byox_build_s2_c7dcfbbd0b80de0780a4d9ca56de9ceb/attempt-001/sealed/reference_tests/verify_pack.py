"""Deterministic archive-boundary checks for this generated challenge pack."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]

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

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_4b62c869e81606deb9eb1148a914808f",
    "provenance_sha256": "723d45f5f13c20ab2ee3916d5ebe0818a5f844d7e5d9e1bfb3ce3fe9001ef06d",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

EXPECTED_PROVENANCE_FILE_SHA256 = (
    "3dc7fc913794fd6c9205f6d0588d0a9c4370fb639ae6991b97b4f28aaff9d57a"
)

MANAGED_ROOTS = [
    "starter",
    "public_tests",
    "environment",
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
]

TEXT_SUFFIXES = {
    "",
    ".c",
    ".ec",
    ".h",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".yaml",
}

CREDENTIAL_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(
        rb"(?i)\b(?:api[_-]?key|password)\s*[:=]\s*[\"'][^\"'\r\n]{8,}"
    ),
]


def fail(message: str) -> None:
    print(f"pack verification: FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def managed_paths() -> list[Path]:
    paths: list[Path] = []
    for relative in REQUIRED:
        path = ROOT / relative
        if path.parent == ROOT:
            paths.append(path)
    for relative in MANAGED_ROOTS:
        root = ROOT / relative
        paths.append(root)
        paths.extend(root.rglob("*"))
    return paths


def main() -> None:
    missing = [relative for relative in REQUIRED if not (ROOT / relative).is_file()]
    if missing:
        fail("missing required regular files: " + ", ".join(missing))

    present_forbidden = [relative for relative in FORBIDDEN if (ROOT / relative).exists()]
    if present_forbidden:
        fail("forbidden paths exist: " + ", ".join(present_forbidden))

    manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
    if manifest != EXPECTED_MANIFEST:
        fail("MANIFEST.yaml differs from its authoritative object")

    provenance_bytes = (ROOT / "PROVENANCE.json").read_bytes()
    try:
        provenance = json.loads(provenance_bytes)
    except json.JSONDecodeError as error:
        fail(f"PROVENANCE.json is not strict JSON: {error}")
    digest = hashlib.sha256(provenance_bytes).hexdigest()
    if digest != EXPECTED_PROVENANCE_FILE_SHA256:
        fail("PROVENANCE.json differs from its immutable checked snapshot")
    if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
        fail("provenance snapshot identifier does not match manifest")

    paths = managed_paths()
    for path in paths:
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            fail(f"non-regular archive entry: {path.relative_to(ROOT)}")

    for path in paths:
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        data = path.read_bytes()
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(data):
                fail(f"credential-like value in {path.relative_to(ROOT)}")

    print("required paths: PASS")
    print("forbidden paths: PASS")
    print("manifest/provenance: PASS")
    print("regular-file boundary: PASS")
    print("credential-pattern scan: PASS")


if __name__ == "__main__":
    main()
