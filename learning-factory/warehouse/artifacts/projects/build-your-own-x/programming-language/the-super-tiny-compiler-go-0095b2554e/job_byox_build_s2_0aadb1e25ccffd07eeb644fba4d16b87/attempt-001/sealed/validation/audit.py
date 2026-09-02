#!/usr/bin/env python3
"""Deterministic structural and credential-pattern audit for this artifact."""

import hashlib
import json
import re
import sys
from pathlib import Path


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
    "MANIFEST.yaml": "4e6c88e18008226e3f64c0e2c366ec6aafb2b859f2a5557054fa3feaed6c1c59",
    "PROVENANCE.json": "d75f0974ef139507894b6414cedf2feb9bcd216eb787792a7f0c3229c01b15df",
}
CREDENTIAL_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "openai-like-key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "google-api-key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "jwt": re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
    ),
    "assigned-password": re.compile(
        r"(?i)\b(?:password|passwd)\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
}


def canonical_digest(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main():
    failures = []
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        failures.append(f"missing required files: {missing}")

    paths = [path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*")]
    forbidden = sorted(
        {
            path
            for path in paths
            for prefix in FORBIDDEN
            if path == prefix or path.startswith(prefix + "/")
        }
    )
    if forbidden:
        failures.append(f"forbidden paths: {forbidden}")

    special = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if not path.is_file() and not path.is_dir()
    ]
    if special:
        failures.append(f"symlinks or special files: {special}")

    for name, expected in CANONICAL_JSON_SHA256.items():
        try:
            actual = canonical_digest(ROOT / name)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            failures.append(f"{name} is not strict readable JSON: {error}")
            continue
        if actual != expected:
            failures.append(f"{name} canonical digest {actual}, expected {expected}")

    manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
    if manifest.get("status") != "GENERATED" or manifest.get("validation_labels") != [
        "GENERATED",
        "PARTIAL",
    ]:
        failures.append("manifest status or labels changed")

    credential_hits = []
    generated_files = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name == ".factory-workspace":
            continue
        generated_files += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in CREDENTIAL_PATTERNS.items():
            if pattern.search(text):
                credential_hits.append(f"{path.relative_to(ROOT)}:{label}")
    if credential_hits:
        failures.append(f"credential-like content: {credential_hits}")

    misplaced_answers = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("ANSWER.md")
        if "sealed" not in path.relative_to(ROOT).parts
    ]
    if misplaced_answers:
        failures.append(f"answers outside an exercise sealed directory: {misplaced_answers}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("required-files: OK")
    print("forbidden-paths: OK")
    print("strict-json-snapshots: OK")
    print("file-types: OK")
    print("credential-patterns: OK")
    print("exercise-answer-isolation: OK")
    print(f"generated-file-count: {generated_files}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
