#!/usr/bin/env python3
"""Deterministic structural, metadata, and limited credential audit."""

import hashlib
import json
import os
import re
import stat
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARTIFACT_ROOTS = (
    "AGENTS.md", "CONCEPTS.md", "DESIGN_QUESTIONS.md",
    "LICENSE_BOUNDARY.md", "MANIFEST.yaml", "PROVENANCE.json", "README.md",
    "REQUIREMENTS.md", "VALIDATION.md", "adversarial", "benchmarks",
    "debugging", "environment", "public_tests", "review_exercises", "sealed",
    "starter",
)
REQUIRED = (
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json",
    "LICENSE_BOUNDARY.md", "REQUIREMENTS.md", "CONCEPTS.md",
    "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter/README.md",
    "public_tests/README.md", "environment/README.md",
    "sealed/reference/README.md", "sealed/reference_tests/README.md",
    "sealed/DESIGN.md", "sealed/TRADEOFFS.md", "sealed/REVIEW.md",
    "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md", "adversarial/README.md",
    "debugging/README.md", "review_exercises/README.md",
    "benchmarks/README.md",
)
FORBIDDEN = (
    ".git", ".env", ".venv", "credentials.json", "secrets", "reference",
    "reference_tests", "hidden_tests", "solution", "solutions", "answers",
    "starter/sealed", "starter/reference", "starter/reference_tests",
    "starter/solution", "starter/solutions", "starter/answers",
    "public_tests/sealed", "public_tests/reference", "public_tests/hidden_tests",
    "environment/sealed",
)
EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_0211acfa0bef3a271027fdcfd888e86a",
    "provenance_sha256": "39c21180cbc5ede2240b48eb399513125810e87c29d484501064179bd9c5b2aa",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}
EXPECTED_LEARNER_ALLOWLIST = {
    "root_directories": ["environment", "public_tests", "starter"],
    "root_files": [
        "AGENTS.md", "CONCEPTS.md", "DESIGN_QUESTIONS.md", "MANIFEST.yaml",
        "README.md", "REQUIREMENTS.md",
    ],
    "schema_version": 1,
}
EXPECTED_PROVENANCE_FILE_SHA256 = (
    "8dec1885294f3e1e88f20ce3eaaec0d6c3cf80e4831e5cb702b07bba4db4a7e4"
)


def reject_constant(value):
    raise ValueError("non-standard JSON constant: {}".format(value))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: {}".format(key))
        result[key] = value
    return result


def strict_json(relative):
    with open(os.path.join(ROOT, relative), "r", encoding="utf-8") as handle:
        return json.load(
            handle, object_pairs_hook=unique_object, parse_constant=reject_constant
        )


def artifact_files():
    files = []
    for artifact_root in ARTIFACT_ROOTS:
        path = os.path.join(ROOT, artifact_root)
        if os.path.isfile(path) and not os.path.islink(path):
            files.append(path)
            continue
        for directory, names, filenames in os.walk(path, followlinks=False):
            for name in names:
                child = os.path.join(directory, name)
                if os.path.islink(child):
                    raise AssertionError("symbolic link: {}".format(child))
            for name in filenames:
                child = os.path.join(directory, name)
                metadata = os.lstat(child)
                if not stat.S_ISREG(metadata.st_mode):
                    raise AssertionError("non-regular file: {}".format(child))
                files.append(child)
    return sorted(set(files))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    for relative in REQUIRED:
        path = os.path.join(ROOT, relative)
        if not os.path.isfile(path) or os.path.islink(path):
            raise AssertionError("required regular file missing: {}".format(relative))
    for relative in FORBIDDEN:
        if os.path.lexists(os.path.join(ROOT, relative)):
            raise AssertionError("forbidden path exists: {}".format(relative))

    manifest = strict_json("MANIFEST.yaml")
    if manifest != EXPECTED_MANIFEST:
        raise AssertionError("MANIFEST.yaml differs from its authoritative object")
    provenance = strict_json("PROVENANCE.json")
    if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
        raise AssertionError("provenance snapshot identifier mismatch")
    provenance_path = os.path.join(ROOT, "PROVENANCE.json")
    if sha256_file(provenance_path) != EXPECTED_PROVENANCE_FILE_SHA256:
        raise AssertionError("PROVENANCE.json bytes differ from immutable snapshot")
    if strict_json("environment/learner_view_allowlist.json") != EXPECTED_LEARNER_ALLOWLIST:
        raise AssertionError("learner-view allowlist differs from policy")

    patterns = (
        re.compile(re.escape("-----" + "BEGIN ") + r"(?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile("g" + r"h[pousr]_[A-Za-z0-9]{20,}"),
        re.compile("s" + r"k-[A-Za-z0-9]{20,}"),
        re.compile(
            r"(?i)\b(?:pass" + r"word|api[_-]?key|secret)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
        ),
    )
    files = artifact_files()
    hits = []
    for path in files:
        with open(path, "rb") as handle:
            data = handle.read()
        relative = os.path.relpath(path, ROOT).replace(os.sep, "/")
        if b"\x00" in data:
            raise AssertionError("literal NUL byte: {}".format(relative))
        text = data.decode("utf-8")
        for pattern in patterns:
            if pattern.search(text):
                hits.append(relative)
                break
    if hits:
        raise AssertionError("credential-pattern hits: {}".format(", ".join(hits)))

    print(
        "pack audit PASS: {} required files, {} forbidden paths absent, "
        "{} UTF-8 regular files, 0 credential-pattern hits".format(
            len(REQUIRED), len(FORBIDDEN), len(files)
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
