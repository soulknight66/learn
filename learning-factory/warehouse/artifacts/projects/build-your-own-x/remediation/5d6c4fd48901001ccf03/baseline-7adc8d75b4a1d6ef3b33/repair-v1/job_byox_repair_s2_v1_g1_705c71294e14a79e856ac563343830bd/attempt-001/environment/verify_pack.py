#!/usr/bin/env python3
"""Deterministic packaging and hygiene checks; not a solution validator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json", "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md", "CONCEPTS.md", "DESIGN_QUESTIONS.md", "VALIDATION.md",
    "starter/README.md", "public_tests/README.md", "environment/README.md",
    "sealed/reference/README.md", "sealed/reference_tests/README.md", "sealed/DESIGN.md",
    "sealed/TRADEOFFS.md", "sealed/REVIEW.md", "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md", "adversarial/README.md", "debugging/README.md",
    "review_exercises/README.md", "benchmarks/README.md",
    "environment/PROVENANCE.sha256",
]
FORBIDDEN = [
    ".git", ".env", ".venv", "credentials.json", "secrets", "reference", "reference_tests",
    "hidden_tests", "solution", "solutions", "answers", "starter/sealed", "starter/reference",
    "starter/reference_tests", "starter/solution", "starter/solutions", "starter/answers",
    "public_tests/sealed", "public_tests/reference", "public_tests/hidden_tests",
    "environment/sealed",
]
EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_884ee11fc61abc48b60825556299dae5",
    "provenance_sha256": "f7190ea0b5ce4b06359e84384b56d25ad265a0faf0bfdd6208378b4a17b5ca5a",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}
EXPECTED_PROVENANCE_DOCUMENT_SHA256 = (
    "1b00a500c586d122105ac591fbb0868281cb0524f989f607326e0a896d75b611"
)
SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
]


def _provenance_document_errors(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        provenance_bytes = (root / "PROVENANCE.json").read_bytes()
        provenance = json.loads(provenance_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"provenance is not strict JSON: {exc}")
    else:
        if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
            errors.append("provenance snapshot binding differs from manifest")
        document_digest = hashlib.sha256(provenance_bytes).hexdigest()
        if document_digest != EXPECTED_PROVENANCE_DOCUMENT_SHA256:
            errors.append("PROVENANCE.json byte digest differs from canonical document")
    expected_digest_line = f"{EXPECTED_PROVENANCE_DOCUMENT_SHA256}  PROVENANCE.json\n"
    try:
        digest_line = (root / "environment/PROVENANCE.sha256").read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"provenance document digest declaration is unreadable: {exc}")
    else:
        if digest_line != expected_digest_line:
            errors.append("provenance document digest declaration differs from canonical digest")
    return errors


def main() -> int:
    errors: list[str] = []
    for name in REQUIRED:
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            errors.append(f"required regular file missing: {name}")
    for name in FORBIDDEN:
        if (ROOT / name).exists() or (ROOT / name).is_symlink():
            errors.append(f"forbidden path exists: {name}")
    for path in ROOT.rglob("*"):
        mode = path.lstat().st_mode
        if path.is_symlink() or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            errors.append(f"non-regular archive entry: {path.relative_to(ROOT)}")
        if stat.S_ISREG(mode):
            data = path.read_bytes()
            for pattern in SECRET_PATTERNS:
                if pattern.search(data):
                    errors.append(f"credential-like content: {path.relative_to(ROOT)}")
    try:
        manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"manifest is not strict JSON: {exc}")
    else:
        if manifest != EXPECTED_MANIFEST:
            errors.append("manifest differs from authoritative object")
    errors.extend(_provenance_document_errors(ROOT))
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"OK: {len(REQUIRED)} required files; forbidden paths absent; regular entries only; metadata and credential scan clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
