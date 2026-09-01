#!/usr/bin/env python3
"""Audit challenge packaging without entering factory-owned hidden paths."""

import hashlib
import json
import os
import re
import stat
import sys


REQUIRED = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json",
    "LICENSE_BOUNDARY.md", "REQUIREMENTS.md", "CONCEPTS.md",
    "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter/README.md",
    "public_tests/README.md", "environment/README.md",
    "sealed/reference/README.md", "sealed/reference_tests/README.md",
    "sealed/DESIGN.md", "sealed/TRADEOFFS.md", "sealed/REVIEW.md",
    "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md", "adversarial/README.md",
    "debugging/README.md", "review_exercises/README.md",
    "benchmarks/README.md"
]

FORBIDDEN = [
    ".git", ".env", ".venv", "credentials.json", "secrets", "reference",
    "reference_tests", "hidden_tests", "solution", "solutions", "answers",
    "starter/sealed", "starter/reference", "starter/reference_tests",
    "starter/solution", "starter/solutions", "starter/answers",
    "public_tests/sealed", "public_tests/reference",
    "public_tests/hidden_tests", "environment/sealed"
]

MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_07eeac43f46abe6b1c4150d7fe7a648c",
    "provenance_sha256":
        "14e4683c18c49bf52fffb640c2fcdf5df5df77986fbd27a25863624dd7d3799d",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"]
}

PROVENANCE_CANONICAL_SHA256 = (
    "d904f811cf8c6ea3d20abff468ccd266a7778a9a49dbe6efb9d2c42b4eef3fac"
)

SCAN_ROOTS = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json",
    "LICENSE_BOUNDARY.md", "REQUIREMENTS.md", "CONCEPTS.md",
    "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter", "public_tests",
    "environment", "sealed", "adversarial", "debugging",
    "review_exercises", "benchmarks"
]

TEXT_SUFFIXES = {".md", ".json", ".yaml", ".c", ".h", ".S", ".ld", ".py", ".sh"}
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(
        r"(?i)(password|passwd|api[_-]?key|access[_-]?token)"
        r"\s*[:=]\s*[\"'][^\"']+[\"']"
    )
]


def canonical_hash(value):
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generated_paths():
    for root in SCAN_ROOTS:
        if os.path.isdir(root):
            for directory, dirnames, filenames in os.walk(root, followlinks=False):
                for name in dirnames:
                    yield os.path.join(directory, name)
                for name in filenames:
                    yield os.path.join(directory, name)
        else:
            yield root


def main():
    errors = []
    regular_count = 0

    for path in REQUIRED:
        if not os.path.exists(path):
            errors.append("missing required path: " + path)
        elif not stat.S_ISREG(os.lstat(path).st_mode):
            errors.append("required path is not a regular file: " + path)
        else:
            regular_count += 1
    for path in FORBIDDEN:
        if os.path.lexists(path):
            errors.append("forbidden path exists: " + path)

    with open("MANIFEST.yaml", "r") as stream:
        manifest = json.load(stream)
    with open("PROVENANCE.json", "r") as stream:
        provenance = json.load(stream)
    if manifest != MANIFEST:
        errors.append("manifest object differs from the authoritative object")
    if canonical_hash(provenance) != PROVENANCE_CANONICAL_SHA256:
        errors.append("provenance object differs from the immutable snapshot")
    if provenance.get("snapshot_sha256") != manifest.get("provenance_sha256"):
        errors.append("manifest/provenance snapshot binding differs")

    symlinks = set()
    credential_hits = []
    for path in generated_paths():
        if os.path.islink(path):
            symlinks.add(path)
            continue
        if not os.path.isfile(path):
            continue
        name = os.path.basename(path)
        suffix = os.path.splitext(path)[1]
        if name != "Makefile" and suffix not in TEXT_SUFFIXES:
            continue
        try:
            with open(path, "r") as stream:
                content = stream.read()
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                credential_hits.append(path)
                break

    errors.extend("generated symlink: " + path for path in sorted(symlinks))
    errors.extend("credential-shaped text: " + path for path in credential_hits)

    print("required regular files: {}/{}".format(regular_count, len(REQUIRED)))
    print("forbidden paths present: {}".format(
        sum(os.path.lexists(path) for path in FORBIDDEN)))
    print("manifest exact object: {}".format(manifest == MANIFEST))
    print("provenance exact canonical object: {}".format(
        canonical_hash(provenance) == PROVENANCE_CANONICAL_SHA256))
    print("symlinks in generated scope: {}".format(len(symlinks)))
    print("credential-shaped matches in generated text: {}".format(
        len(credential_hits)))

    if errors:
        for error in errors:
            print("AUDIT ERROR: " + error, file=sys.stderr)
        return 1
    print("artifact audit: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
