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

CREDENTIAL_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(
        rb"(?i)\b(?:api[_-]?key|password)\s*[:=]\s*[\"'][^\"'\r\n]{8,}"
    ),
]


ALLOWED_TOP_LEVEL = {
    *(Path(relative).parts[0] for relative in REQUIRED),
    *MANAGED_ROOTS,
}


class VerificationError(RuntimeError):
    """A deterministic challenge-pack contract violation."""


def fail(message: str) -> None:
    raise VerificationError(message)


def archive_paths(root: Path) -> list[Path]:
    """Return every entry without following a symlinked directory."""
    top_level = sorted(root.iterdir(), key=lambda path: path.name)
    unexpected = [path.name for path in top_level if path.name not in ALLOWED_TOP_LEVEL]
    if unexpected:
        fail("unexpected top-level entries: " + ", ".join(unexpected))

    paths: list[Path] = []
    pending = list(reversed(top_level))
    while pending:
        path = pending.pop()
        try:
            mode = path.lstat().st_mode
        except OSError as error:
            fail(f"cannot inspect {path.relative_to(root)}: {error}")
        paths.append(path)
        if stat.S_ISDIR(mode):
            try:
                children = sorted(path.iterdir(), key=lambda child: child.name)
            except OSError as error:
                fail(f"cannot enumerate {path.relative_to(root)}: {error}")
            pending.extend(reversed(children))
    return paths


def is_regular_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def entry_exists(path: Path) -> bool:
    try:
        path.lstat()
        return True
    except FileNotFoundError:
        return False
    except OSError as error:
        fail(f"cannot inspect {path}: {error}")


def verify(root: Path = ROOT) -> list[str]:
    missing = [relative for relative in REQUIRED if not is_regular_file(root / relative)]
    if missing:
        fail("missing required regular files: " + ", ".join(missing))

    present_forbidden = [relative for relative in FORBIDDEN if entry_exists(root / relative)]
    if present_forbidden:
        fail("forbidden paths exist: " + ", ".join(present_forbidden))

    try:
        manifest = json.loads((root / "MANIFEST.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"MANIFEST.yaml is not readable strict JSON: {error}")
    if manifest != EXPECTED_MANIFEST:
        fail("MANIFEST.yaml differs from its authoritative object")

    provenance_bytes = (root / "PROVENANCE.json").read_bytes()
    try:
        provenance = json.loads(provenance_bytes)
    except json.JSONDecodeError as error:
        fail(f"PROVENANCE.json is not strict JSON: {error}")
    digest = hashlib.sha256(provenance_bytes).hexdigest()
    if digest != EXPECTED_PROVENANCE_FILE_SHA256:
        fail("PROVENANCE.json differs from its immutable checked snapshot")
    if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
        fail("provenance snapshot identifier does not match manifest")

    paths = archive_paths(root)
    for path in paths:
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            fail(f"non-regular archive entry: {path.relative_to(root)}")

    for path in paths:
        if not is_regular_file(path):
            continue
        data = path.read_bytes()
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(data):
                fail(f"credential-like value in {path.relative_to(root)}")

    return [
        "required paths: PASS",
        "forbidden paths: PASS",
        "manifest/provenance: PASS",
        "top-level allowlist: PASS",
        "regular-file boundary: PASS",
        "whole-archive credential-pattern scan: PASS",
    ]


def main() -> None:
    try:
        messages = verify()
    except VerificationError as error:
        print(f"pack verification: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from None
    for message in messages:
        print(message)


if __name__ == "__main__":
    main()
