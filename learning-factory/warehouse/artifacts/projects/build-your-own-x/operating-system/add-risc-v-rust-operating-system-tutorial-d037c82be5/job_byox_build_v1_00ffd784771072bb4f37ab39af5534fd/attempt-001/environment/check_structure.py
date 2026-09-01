"""Deterministic structural and leak checks for the generated challenge pack."""

import json
import hashlib
import re
import stat
import sys
from pathlib import Path
from typing import List


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
    "project_id": "project_1d0f3c2883c1fe71745b209f353ce81d",
    "provenance_sha256": "de20a4a1722e49e6e330819419715c89a106d555a1de62066f144193f4e67355",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

EXPECTED_PROVENANCE_CANONICAL_SHA256 = (
    "eae7157c5a99d853342624ca3811dfe050fadec0df3f0de52d7de0bec278b607"
)

# Assemble signatures so this checker does not flag its own source literals.
PRIVATE_KEY_RE = re.compile(
    "-----BEGIN " + r"(?:RSA|OPENSSH|EC|DSA)" + " PRIVATE KEY-----"
)
AWS_ACCESS_RE = re.compile("AK" + r"IA[0-9A-Z]{16}")
ASSIGNED_SECRET_RE = re.compile(
    r"(?i)\b(?:password|api[_-]?key|access[_-]?token|client[_-]?secret)\b"
    r"\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]"
)


def fail(message: str, failures: List[str]) -> None:
    failures.append(message)


def main() -> int:
    failures = []  # type: List[str]

    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            fail(f"required regular file missing: {relative}", failures)

    for relative in FORBIDDEN:
        if (ROOT / relative).exists() or (ROOT / relative).is_symlink():
            fail(f"forbidden path exists: {relative}", failures)

    for path in ROOT.rglob("*"):
        mode = path.lstat().st_mode
        if path.is_symlink() or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            fail(f"non-regular/non-directory archive entry: {path.relative_to(ROOT)}", failures)

    try:
        manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"MANIFEST.yaml is not strict JSON: {error}", failures)
    else:
        if manifest != EXPECTED_MANIFEST:
            fail("MANIFEST.yaml differs from the authoritative object", failures)

    try:
        provenance = json.loads((ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"PROVENANCE.json is not strict JSON: {error}", failures)
    else:
        canonical = json.dumps(
            provenance,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if hashlib.sha256(canonical).hexdigest() != EXPECTED_PROVENANCE_CANONICAL_SHA256:
            fail("PROVENANCE.json differs from the authoritative object", failures)
        expected_identity = (
            1,
            "de20a4a1722e49e6e330819419715c89a106d555a1de62066f144193f4e67355",
            "project_1d0f3c2883c1fe71745b209f353ce81d",
            "source_eac489a34bed5db9a1f2a580b457bcef",
            "aa17439b62f384511a5561ce308e9598b94d8989",
            False,
        )
        observed_identity = (
            provenance.get("schema_version"),
            provenance.get("snapshot_sha256"),
            provenance.get("project", {}).get("project_id"),
            provenance.get("source", {}).get("source_id"),
            provenance.get("source", {}).get("commit_hash"),
            provenance.get("license_boundary", {}).get("linked_content_copied"),
        )
        if observed_identity != expected_identity:
            fail("PROVENANCE.json immutable identity fields differ", failures)

    patterns = (PRIVATE_KEY_RE, AWS_ACCESS_RE, ASSIGNED_SECRET_RE)
    excluded = {Path("environment/check_structure.py")}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(ROOT)
        if relative in excluded or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            if any(pattern.search(line) for pattern in patterns):
                fail(f"credential-shaped text: {relative}:{line_number}", failures)

    if failures:
        for message in failures:
            print(f"FAIL: {message}")
        print(f"STRUCTURE_CHECK: FAIL ({len(failures)} issue(s))")
        return 1
    print(f"STRUCTURE_CHECK: PASS ({len(REQUIRED)} required paths, {len(FORBIDDEN)} forbidden paths)")
    print("MANIFEST_CHECK: PASS (strict JSON and exact object)")
    print("PROVENANCE_CHECK: PASS (exact canonical object and immutable identity)")
    print("ENTRY_TYPE_CHECK: PASS (directories and regular files only)")
    print("CREDENTIAL_SHAPE_SCAN: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
