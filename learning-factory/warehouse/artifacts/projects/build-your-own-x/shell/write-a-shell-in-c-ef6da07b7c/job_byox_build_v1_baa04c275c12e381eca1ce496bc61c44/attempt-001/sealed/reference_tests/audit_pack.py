#!/usr/bin/env python3
"""Deterministic structural, metadata, special-file, and credential audit."""

import json
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]

GENERATED_ROOT_ENTRIES = {
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json",
    "LICENSE_BOUNDARY.md", "REQUIREMENTS.md", "CONCEPTS.md",
    "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter", "public_tests",
    "environment", "sealed", "adversarial", "debugging", "review_exercises",
    "benchmarks",
}

REQUIRED = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json",
    "LICENSE_BOUNDARY.md", "REQUIREMENTS.md", "CONCEPTS.md",
    "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter/README.md",
    "public_tests/README.md", "environment/README.md",
    "sealed/reference/README.md", "sealed/reference_tests/README.md",
    "sealed/DESIGN.md", "sealed/TRADEOFFS.md", "sealed/REVIEW.md",
    "sealed/alternatives/README.md", "sealed/production/PRODUCTIONIZATION.md",
    "adversarial/README.md", "debugging/README.md",
    "review_exercises/README.md", "benchmarks/README.md",
]

FORBIDDEN = [
    ".git", ".env", ".venv", "credentials.json", "secrets", "reference",
    "reference_tests", "hidden_tests", "solution", "solutions", "answers",
    "starter/sealed", "starter/reference", "starter/reference_tests",
    "starter/solution", "starter/solutions", "starter/answers",
    "public_tests/sealed", "public_tests/reference", "public_tests/hidden_tests",
    "environment/sealed",
]

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_174888fa5782c93127ae604fcdd4913a",
    "provenance_sha256": "8c9dfcfc0a7e11722572b7efd0dab0f02bca8ee03eb87027356598182ae4a9ee",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}


def fail(message):
    print("AUDIT ERROR: " + message, file=sys.stderr)
    return 1


def generated_paths():
    for entry in sorted(GENERATED_ROOT_ENTRIES):
        path = ROOT / entry
        if path.exists():
            yield path
            if path.is_dir():
                for child in path.rglob("*"):
                    yield child


def main():
    errors = 0

    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file():
            errors += fail("missing required regular file: " + relative)
    if not errors:
        print("required paths: present")

    forbidden_found = [relative for relative in FORBIDDEN if (ROOT / relative).exists()]
    if forbidden_found:
        errors += fail("forbidden paths exist: " + ", ".join(forbidden_found))
    else:
        print("forbidden paths: absent")

    for path in generated_paths():
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            errors += fail("non-regular artifact: " + str(path.relative_to(ROOT)))
    if not errors:
        print("filesystem objects: regular files and directories only")

    try:
        manifest = json.loads((ROOT / "MANIFEST.yaml").read_text())
    except (OSError, ValueError) as error:
        errors += fail("manifest is not strict JSON: " + str(error))
    else:
        if manifest != EXPECTED_MANIFEST:
            errors += fail("manifest object differs from immutable expectation")
        else:
            print("manifest: exact expected object")

    try:
        provenance = json.loads((ROOT / "PROVENANCE.json").read_text())
    except (OSError, ValueError) as error:
        errors += fail("provenance is not strict JSON: " + str(error))
    else:
        if (provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"] or
                provenance.get("project", {}).get("project_id") != EXPECTED_MANIFEST["project_id"] or
                provenance.get("source", {}).get("commit_hash") != EXPECTED_MANIFEST["source_commit"]):
            errors += fail("provenance binding fields differ")
        else:
            print("provenance: JSON and binding fields verified")

    sensitive_patterns = [
        re.compile("-----BEGIN " + "PRIVATE KEY-----"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(("(?i)(api[_-]?key|secret[_-]?key|pass" +
                    "word)\\s*[:=]\\s*['\"]([^'\"]{8,})['\"]")),
    ]
    for path in generated_paths():
        if not path.is_file() or path == Path(__file__).resolve():
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in sensitive_patterns:
            if pattern.search(text):
                errors += fail("credential-like content in " + str(path.relative_to(ROOT)))
                break
    if not errors:
        print("credential signatures: none detected")

    if errors:
        print("AUDIT FAILED: {} issue(s)".format(errors), file=sys.stderr)
        return 1
    print("AUDIT OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
