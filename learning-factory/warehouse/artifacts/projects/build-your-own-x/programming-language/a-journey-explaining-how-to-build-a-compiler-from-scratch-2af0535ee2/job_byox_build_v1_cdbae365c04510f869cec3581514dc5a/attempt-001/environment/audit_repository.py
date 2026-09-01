#!/usr/bin/env python3
"""Deterministic structural and secret-pattern audit for this generated pack."""

import hashlib
import json
import os
import re
import stat
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
GENERATED_TOP = (
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json",
    "LICENSE_BOUNDARY.md", "REQUIREMENTS.md", "CONCEPTS.md",
    "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter", "public_tests",
    "environment", "sealed", "adversarial", "debugging", "review_exercises",
    "benchmarks",
)
EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_ef449ee88f318bad30bec20a8941022d",
    "provenance_sha256": "a352640b7e055e83e7c856a44576b2a3b92ed775ecb1d881d399163221097a16",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}
EXPECTED_PROVENANCE_CANONICAL_SHA256 = (
    "b1a0bbc2feaff012132039bd8ded15748d618243b357b1c01dc32fbcd02d9fe0"
)
CREDENTIAL_PATTERNS = (
    re.compile(br"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(br"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(br"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(br"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(br"\bxox[baprs]-[A-Za-z0-9-]{12,}\b"),
    re.compile(
        br"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token)\b"
        br"\s*[:=]\s*[\"'][^\"'\r\n]{4,}[\"']"
    ),
    re.compile(br"[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s:@]+:[^/\s@]+@"),
)


def fail(messages, message):
    messages.append(message)


def generated_paths():
    for relative in GENERATED_TOP:
        absolute = os.path.join(ROOT, relative)
        if os.path.isdir(absolute) and not os.path.islink(absolute):
            yield absolute
            for directory, names, files in os.walk(absolute, followlinks=False):
                for name in names:
                    yield os.path.join(directory, name)
                for name in files:
                    yield os.path.join(directory, name)
        elif os.path.lexists(absolute):
            yield absolute


def main():
    failures = []
    for relative in REQUIRED:
        if not os.path.isfile(os.path.join(ROOT, relative)):
            fail(failures, "missing required regular file: " + relative)
    for relative in FORBIDDEN:
        if os.path.lexists(os.path.join(ROOT, relative)):
            fail(failures, "forbidden path exists: " + relative)

    seen = set()
    regular_files = []
    for absolute in generated_paths():
        if absolute in seen:
            continue
        seen.add(absolute)
        mode = os.lstat(absolute).st_mode
        relative = os.path.relpath(absolute, ROOT)
        if stat.S_ISLNK(mode):
            fail(failures, "symlink exists: " + relative)
        elif stat.S_ISREG(mode):
            regular_files.append(absolute)
        elif not stat.S_ISDIR(mode):
            fail(failures, "special file exists: " + relative)

    try:
        with open(os.path.join(ROOT, "MANIFEST.yaml"), "r", encoding="utf-8") as stream:
            manifest = json.load(stream)
        if manifest != EXPECTED_MANIFEST:
            fail(failures, "MANIFEST.yaml does not equal the required JSON object")
    except (OSError, ValueError) as error:
        fail(failures, "MANIFEST.yaml is not strict JSON: " + str(error))

    try:
        with open(os.path.join(ROOT, "PROVENANCE.json"), "r", encoding="utf-8") as stream:
            provenance = json.load(stream)
        canonical = json.dumps(
            provenance, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        digest = hashlib.sha256(canonical).hexdigest()
        if digest != EXPECTED_PROVENANCE_CANONICAL_SHA256:
            fail(failures, "PROVENANCE.json does not equal the immutable snapshot")
        if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
            fail(failures, "provenance snapshot identifier mismatch")
    except (OSError, ValueError) as error:
        fail(failures, "PROVENANCE.json is not strict JSON: " + str(error))

    for absolute in regular_files:
        with open(absolute, "rb") as stream:
            data = stream.read()
        if b"\0" in data:
            continue
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(data):
                fail(
                    failures,
                    "credential-like pattern in " + os.path.relpath(absolute, ROOT),
                )
                break

    if failures:
        for message in failures:
            print("audit: FAIL: " + message, file=sys.stderr)
        return 1
    print("audit: required paths present: %d" % len(REQUIRED))
    print("audit: forbidden paths absent: %d" % len(FORBIDDEN))
    print("audit: generated tree contains regular files/directories only")
    print("audit: manifest and provenance objects match")
    print("audit: no credential-like text patterns found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
