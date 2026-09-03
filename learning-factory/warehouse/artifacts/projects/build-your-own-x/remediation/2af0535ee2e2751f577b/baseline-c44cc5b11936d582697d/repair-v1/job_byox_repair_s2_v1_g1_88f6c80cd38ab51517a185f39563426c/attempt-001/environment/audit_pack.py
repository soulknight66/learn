#!/usr/bin/env python3
"""Deterministically audit the generated challenge-pack boundary."""

from __future__ import print_function

import hashlib
import json
import os
import re
import stat
import sys


REQUIRED_FILES = (
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

FORBIDDEN_PATHS = (
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

GENERATED_TOP_LEVEL = (
    "AGENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "LICENSE_BOUNDARY.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "README.md",
    "REQUIREMENTS.md",
    "VALIDATION.md",
    "adversarial",
    "benchmarks",
    "debugging",
    "environment",
    "public_tests",
    "review_exercises",
    "sealed",
    "starter",
)

FACTORY_TOP_LEVEL = (
    ".agents",
    ".codex",
    ".factory-workspace",
    "PRIOR_BUILD",
    "PRIOR_REVIEW",
)

CREDENTIAL_PATTERNS = (
    ("private-key-header",
     re.compile(rb"-{5}BEGIN [A-Z0-9 ]*PRIVATE KEY-{5}")),
    ("aws-access-key", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("openai-token", re.compile(rb"\bsk-[A-Za-z0-9]{20,}\b")),
    ("assigned-secret", re.compile(
        rb"(?i)\b(?:password|api[_-]?key|client[_-]?secret)\b"
        rb"\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{8,}")),
)

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_ef449ee88f318bad30bec20a8941022d",
    "provenance_sha256":
        "f1f47fcb8f8bbf8afc1dccfabb601c801393cb2a0f7a005cf040b4001eab6e62",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

EXPECTED_METADATA_HASHES = {
    "MANIFEST.yaml":
        "d790bd7487c566f570a0207bb94f3cf1d2af4815acb04f3d14153bde62600c8e",
    "PROVENANCE.json":
        "db3da454c4b0e7f852e59a264c6e2296b2dd561c35ca2b5bf5f8f9b04d127169",
}


def walk_entries(root, relative):
    path = os.path.join(root, relative)
    metadata = os.lstat(path)
    yield relative, metadata
    if stat.S_ISDIR(metadata.st_mode):
        for name in sorted(os.listdir(path)):
            child = os.path.join(relative, name)
            for item in walk_entries(root, child):
                yield item


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def load_strict_json(path):
    with open(path, "rb") as source:
        content = source.read()
    value = json.loads(content.decode("utf-8"),
                       object_pairs_hook=reject_duplicate_keys)
    return content, value


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    failures = []

    metadata_hashes = {}
    try:
        manifest_bytes, manifest = load_strict_json(
            os.path.join(root, "MANIFEST.yaml"))
        provenance_bytes, provenance = load_strict_json(
            os.path.join(root, "PROVENANCE.json"))
        metadata_hashes["MANIFEST.yaml"] = hashlib.sha256(
            manifest_bytes).hexdigest()
        metadata_hashes["PROVENANCE.json"] = hashlib.sha256(
            provenance_bytes).hexdigest()
        if manifest != EXPECTED_MANIFEST:
            failures.append("MANIFEST.yaml differs from the contract object")
        if not isinstance(provenance, dict):
            failures.append("PROVENANCE.json root is not an object")
        for name, expected in EXPECTED_METADATA_HASHES.items():
            if metadata_hashes.get(name) != expected:
                failures.append(name + " differs from its immutable bytes")
    except (IOError, UnicodeError, ValueError) as error:
        failures.append("metadata JSON error: " + str(error))

    missing = []
    for relative in REQUIRED_FILES:
        path = os.path.join(root, relative)
        if not os.path.isfile(path) or os.path.islink(path):
            missing.append(relative)
    if missing:
        failures.extend("missing required file: " + item for item in missing)

    forbidden = []
    for relative in FORBIDDEN_PATHS:
        if os.path.lexists(os.path.join(root, relative)):
            forbidden.append(relative)
    if forbidden:
        failures.extend("forbidden path present: " + item for item in forbidden)

    known_top = set(GENERATED_TOP_LEVEL) | set(FACTORY_TOP_LEVEL)
    unexpected_top = sorted(set(os.listdir(root)) - known_top)
    failures.extend("unexpected top-level entry: " + item
                    for item in unexpected_top)

    special = []
    credential_matches = []
    for top in GENERATED_TOP_LEVEL:
        if not os.path.lexists(os.path.join(root, top)):
            continue
        for relative, metadata in walk_entries(root, top):
            if not (stat.S_ISREG(metadata.st_mode) or
                    stat.S_ISDIR(metadata.st_mode)):
                special.append(relative)
                continue
            if not stat.S_ISREG(metadata.st_mode):
                continue
            if "build" in relative.split(os.sep):
                continue
            with open(os.path.join(root, relative), "rb") as source:
                content = source.read()
            for label, pattern in CREDENTIAL_PATTERNS:
                if pattern.search(content):
                    credential_matches.append((relative, label))

    failures.extend("special file or symlink: " + item for item in special)
    failures.extend("credential pattern %s in %s" % (label, relative)
                    for relative, label in credential_matches)

    print("required_files=%d missing=%d" %
          (len(REQUIRED_FILES), len(missing)))
    print("forbidden_paths_present=%d" % len(forbidden))
    print("unexpected_top_level_entries=%d" % len(unexpected_top))
    print("generated_special_files_or_symlinks=%d" % len(special))
    print("credential_pattern_matches=%d" % len(credential_matches))
    for name in sorted(metadata_hashes):
        print("%s_sha256=%s" % (name, metadata_hashes[name]))
    if failures:
        for failure in failures:
            print("audit error: " + failure, file=sys.stderr)
        print("pack audit: FAIL", file=sys.stderr)
        return 1
    print("pack audit: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
