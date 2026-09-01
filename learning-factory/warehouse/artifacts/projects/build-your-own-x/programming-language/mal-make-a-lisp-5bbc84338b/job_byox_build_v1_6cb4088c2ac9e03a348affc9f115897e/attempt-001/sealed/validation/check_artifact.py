"""Deterministic generation-time structure and metadata checks."""

from __future__ import print_function

import hashlib
import io
import json
import os
import re
import stat


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

REQUIRED = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json", "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md", "CONCEPTS.md", "DESIGN_QUESTIONS.md", "VALIDATION.md",
    "starter/README.md", "public_tests/README.md", "environment/README.md",
    "sealed/reference/README.md", "sealed/reference_tests/README.md", "sealed/DESIGN.md",
    "sealed/TRADEOFFS.md", "sealed/REVIEW.md", "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md", "adversarial/README.md", "debugging/README.md",
    "review_exercises/README.md", "benchmarks/README.md",
]

FORBIDDEN = [
    ".git", ".env", ".venv", "credentials.json", "secrets", "reference",
    "reference_tests", "hidden_tests", "solution", "solutions", "answers",
    "starter/sealed", "starter/reference", "starter/reference_tests", "starter/solution",
    "starter/solutions", "starter/answers", "public_tests/sealed", "public_tests/reference",
    "public_tests/hidden_tests", "environment/sealed",
]

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_d49f1492abb05519b3c18d8a793d37a2",
    "provenance_sha256": "cc72502200317872a1c6e6118ef52522cea1196554b0909d91006a6fecb0f068",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

PROVENANCE_FILE_SHA256 = "1bb8ebbb6979886568adc0895e34ebe29108cf38ebfc2fee20427012e5cc75b1"

ARTIFACT_ENTRIES = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json", "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md", "CONCEPTS.md", "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter",
    "public_tests", "environment", "sealed", "adversarial", "debugging", "review_exercises",
    "benchmarks",
]

CREDENTIAL_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(
        r"(?i)(api[_-]?key|password|passwd|secret|access[_-]?token)\s*[:=]\s*['\"][^'\"]{4,}"
    ),
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
]


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: {0}".format(key))
        result[key] = value
    return result


def load_json(path):
    with io.open(path, "r", encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=strict_object)


def artifact_paths():
    for entry in ARTIFACT_ENTRIES:
        path = os.path.join(ROOT, entry)
        if os.path.isdir(path) and not os.path.islink(path):
            for directory, names, files in os.walk(path):
                yield directory
                for name in names:
                    yield os.path.join(directory, name)
                for name in files:
                    yield os.path.join(directory, name)
        else:
            yield path


def main():
    missing = [path for path in REQUIRED if not os.path.isfile(os.path.join(ROOT, path))]
    if missing:
        raise AssertionError("missing required files: {0}".format(missing))
    present_forbidden = [path for path in FORBIDDEN if os.path.lexists(os.path.join(ROOT, path))]
    if present_forbidden:
        raise AssertionError("forbidden paths present: {0}".format(present_forbidden))

    nodes = set(artifact_paths())
    irregular = []
    symlinks = []
    for path in nodes:
        mode = os.lstat(path).st_mode
        if stat.S_ISLNK(mode):
            symlinks.append(path)
        elif not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            irregular.append(path)
    if symlinks or irregular:
        raise AssertionError("non-regular artifact nodes: {0}".format(symlinks + irregular))

    manifest = load_json(os.path.join(ROOT, "MANIFEST.yaml"))
    if manifest != EXPECTED_MANIFEST:
        raise AssertionError("manifest differs from authoritative object")
    provenance_path = os.path.join(ROOT, "PROVENANCE.json")
    with open(provenance_path, "rb") as handle:
        provenance_raw = handle.read()
    provenance_hash = hashlib.sha256(provenance_raw).hexdigest()
    if provenance_hash != PROVENANCE_FILE_SHA256:
        raise AssertionError("provenance file changed")
    provenance = load_json(provenance_path)
    if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
        raise AssertionError("provenance snapshot identity differs")

    matches = []
    for path in nodes:
        if not os.path.isfile(path) or os.path.splitext(path)[1] not in (".md", ".py", ".json", ".yaml"):
            continue
        with io.open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(content):
                matches.append(os.path.relpath(path, ROOT))
                break
    if matches:
        raise AssertionError("credential-like patterns found: {0}".format(sorted(matches)))

    print("required_paths={0}/{0}".format(len(REQUIRED)))
    print("forbidden_paths=absent ({0} checked)".format(len(FORBIDDEN)))
    print("artifact_nodes={0} regular_files_or_directories=yes symlinks=0".format(len(nodes)))
    print("manifest=exact strict_json=yes")
    print("provenance=strict_json=yes raw_sha256={0}".format(provenance_hash))
    print("credential_pattern_matches=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
