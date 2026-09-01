#!/usr/bin/env python3
"""Deterministic structural checks for the generated challenge pack."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]

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

CANONICAL_JSON_SHA256 = {
    "MANIFEST.yaml": "1b9528b2afdc23dd22d265e7d0d09033b9908f661bc84f82ebbc8a4fb20cbb18",
    "PROVENANCE.json": "c24359e1e81bcd65754e9fa978df2413709f99aabe63c0bb224fbcc378156217",
}

CREDENTIAL_PATTERNS = {
    "private-key header": re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    "assigned secret": re.compile(
        rb"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token)"
        rb"\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
}


def fail(message: str) -> None:
    print(f"FAIL {message}")
    raise SystemExit(1)


def canonical_hash(path: Path) -> str:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def all_entries():
    entries = []
    for directory, directories, filenames in os.walk(ROOT, followlinks=False):
        base = Path(directory)
        entries.extend(base / name for name in directories)
        entries.extend(base / name for name in filenames)
    return entries


def main() -> int:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        fail(f"missing required files: {missing}")
    print(f"PASS required files present: {len(REQUIRED)}")

    present = [name for name in FORBIDDEN if os.path.lexists(ROOT / name)]
    if present:
        fail(f"forbidden paths present: {present}")
    print(f"PASS forbidden paths absent: {len(FORBIDDEN)}")

    entries = all_entries()
    special = []
    for path in entries:
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            special.append(str(path.relative_to(ROOT)))
    if special:
        fail(f"symlink or special entries present: {special}")
    print(f"PASS all archived entries are regular files/directories: {len(entries)}")

    for name, expected in CANONICAL_JSON_SHA256.items():
        actual = canonical_hash(ROOT / name)
        if actual != expected:
            fail(f"canonical JSON mismatch for {name}: {actual}")
    manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
    if manifest.get("status") != "GENERATED" or manifest.get("validation_labels") != [
        "GENERATED",
        "PARTIAL",
    ]:
        fail("manifest status or labels changed")
    print("PASS immutable JSON and GENERATED/PARTIAL labels match")

    excluded = {"JOB.md", ".factory-workspace"}
    hits = []
    scanned = 0
    for path in entries:
        if not path.is_file() or path.relative_to(ROOT).as_posix() in excluded:
            continue
        scanned += 1
        data = path.read_bytes()
        for label, pattern in CREDENTIAL_PATTERNS.items():
            if pattern.search(data):
                hits.append(f"{path.relative_to(ROOT)} ({label})")
    if hits:
        fail(f"credential-like patterns found: {hits}")
    print(f"PASS no credential-like patterns in generated files: {scanned}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
