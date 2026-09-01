#!/usr/bin/env python3
"""Deterministic structural, metadata, disclosure, and credential audit."""

from __future__ import print_function

import hashlib
import json
import os
import re
import stat
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

PACK_TOP = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json",
    "LICENSE_BOUNDARY.md", "REQUIREMENTS.md", "CONCEPTS.md",
    "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter", "public_tests",
    "environment", "sealed", "adversarial", "debugging", "review_exercises",
    "benchmarks",
]

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_4b62c869e81606deb9eb1148a914808f",
    "provenance_sha256": "160b477880d2a21e41dc2db0d61611f467ae20b893c1dd44e98a55d53c192632",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

EXPECTED_PROVENANCE_FILE_SHA256 = (
    "7d163264fd18e6ecaf9a2efd9c23d95b0f16ad143aa02ac4eca6c14f26a89bb6"
)

CREDENTIAL_PATTERNS = [
    re.compile(b"-----BEGIN " + b"(?:RSA |EC |OPENSSH )?" + b"PRIVATE KEY-----"),
    re.compile(b"AKIA[0-9A-Z]{16}"),
    re.compile(b"gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(b"sk-[A-Za-z0-9]{20,}"),
    re.compile(
        b"(?i)(?:password|passwd|api[_-]?key|access[_-]?key|client[_-]?secret)"
        b"[ \\t]*[:=][ \\t]*['\\\"][^'\\\"\\r\\n]+"
    ),
]


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: {}".format(key))
        result[key] = value
    return result


def load_strict_json(relative_path):
    path = os.path.join(ROOT, relative_path)
    with open(path, "r") as handle:
        return json.load(handle, object_pairs_hook=reject_duplicate_keys)


def file_sha256(relative_path):
    digest = hashlib.sha256()
    with open(os.path.join(ROOT, relative_path), "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pack_paths():
    for top in PACK_TOP:
        absolute = os.path.join(ROOT, top)
        if not os.path.lexists(absolute):
            continue
        yield top, absolute
        if os.path.isdir(absolute) and not os.path.islink(absolute):
            for directory, names, files in os.walk(absolute):
                names.sort()
                files.sort()
                for name in names + files:
                    path = os.path.join(directory, name)
                    yield os.path.relpath(path, ROOT), path


def main():
    failures = []
    missing = [path for path in REQUIRED if not os.path.isfile(os.path.join(ROOT, path))]
    forbidden = [path for path in FORBIDDEN if os.path.lexists(os.path.join(ROOT, path))]
    special = []
    credential_hits = []
    disclosure = []

    manifest = load_strict_json("MANIFEST.yaml")
    provenance = load_strict_json("PROVENANCE.json")
    manifest_sha = file_sha256("MANIFEST.yaml")
    provenance_sha = file_sha256("PROVENANCE.json")

    if manifest != EXPECTED_MANIFEST:
        failures.append("MANIFEST.yaml differs from the immutable contract")
    if provenance_sha != EXPECTED_PROVENANCE_FILE_SHA256:
        failures.append("PROVENANCE.json differs from the immutable contract")
    if manifest.get("project_id") != provenance.get("project", {}).get("project_id"):
        failures.append("project_id mismatch")
    if manifest.get("source_id") != provenance.get("project", {}).get("source_id"):
        failures.append("source_id mismatch")
    if manifest.get("provenance_sha256") != provenance.get("snapshot_sha256"):
        failures.append("provenance snapshot mismatch")

    for relative, absolute in pack_paths():
        mode = os.lstat(absolute).st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            special.append(relative)
            continue
        if not stat.S_ISREG(mode):
            continue
        with open(absolute, "rb") as handle:
            data = handle.read()
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(data):
                credential_hits.append(relative)
                break
        normalized = relative.replace(os.sep, "/")
        if os.path.basename(relative) == "ANSWER.md" and not normalized.startswith("sealed/"):
            disclosure.append(relative)
        if relative.endswith(".c") and not (
                normalized.startswith("sealed/") or normalized.startswith("starter/")):
            disclosure.append(relative)

    failures.extend("missing required path: {}".format(path) for path in missing)
    failures.extend("forbidden path: {}".format(path) for path in forbidden)
    failures.extend("special file: {}".format(path) for path in special)
    failures.extend("credential signature: {}".format(path) for path in credential_hits)
    failures.extend("disclosure violation: {}".format(path) for path in disclosure)

    print("STRICT_JSON MANIFEST.yaml sha256={}".format(manifest_sha))
    print("STRICT_JSON PROVENANCE.json sha256={}".format(provenance_sha))
    print(
        "AUDIT required_paths={} missing={} forbidden={} special_files={} "
        "credential_hits={} disclosure_violations={}".format(
            len(REQUIRED), len(missing), len(forbidden), len(special),
            len(credential_hits), len(disclosure))
    )
    print("STATUS {} labels={} productionized={}".format(
        manifest.get("status"), ",".join(manifest.get("validation_labels", [])),
        str(manifest.get("productionized")).lower()))
    for failure in failures:
        print("FAIL {}".format(failure), file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
