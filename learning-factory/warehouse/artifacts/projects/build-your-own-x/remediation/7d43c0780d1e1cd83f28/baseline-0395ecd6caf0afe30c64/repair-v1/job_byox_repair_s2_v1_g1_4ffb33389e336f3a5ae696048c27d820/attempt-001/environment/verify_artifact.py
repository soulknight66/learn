#!/usr/bin/env python3

from __future__ import print_function

import hashlib
import json
import os
import re
import stat
import sys

sys.dont_write_bytecode = True

from learner_view import (  # noqa: E402 - bytecode policy must be set first
    LEARNER_ROOTS,
    ProjectionError,
    inventory_counts,
    source_inventory,
)


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
    "environment/learner_view.py",
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

ARTIFACT_ROOTS = [
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "VALIDATION.md",
    "starter",
    "public_tests",
    "environment",
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
]

EXPECTED_CANONICAL_HASHES = {
    "MANIFEST.yaml": "e2299a901563deda64a2679fbf65a36440bfbbc54206f834f3ce438dec98aab3",
    "PROVENANCE.json": "8830de4919fec4723ad5ea1219617b2d1c75a922aa1f3fe0e02152c6e90d9e1d",
}

CREDENTIAL_PATTERNS = [
    re.compile(br"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(br"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(br"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(br"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(
        br"""(?ix)
        \b(?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token)
        \s*[:=]\s*["'][^"'\r\n]{8,}["']
        """
    ),
]


def fail(message):
    print("FAIL: {}".format(message), file=sys.stderr)
    raise SystemExit(1)


def canonical_hash(path):
    with open(path, "r") as handle:
        value = json.load(handle)
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), value


def artifact_entries():
    for root in ARTIFACT_ROOTS:
        if not os.path.lexists(root):
            continue
        yield root
        if os.path.isdir(root) and not os.path.islink(root):
            for parent, directories, files in os.walk(root):
                directories.sort()
                files.sort()
                for name in directories:
                    yield os.path.join(parent, name)
                for name in files:
                    yield os.path.join(parent, name)


def main():
    missing = [path for path in REQUIRED if not os.path.isfile(path)]
    if missing:
        fail("missing required paths: {}".format(", ".join(missing)))
    print("required_paths: PASS ({}/{})".format(len(REQUIRED), len(REQUIRED)))

    present = [path for path in FORBIDDEN if os.path.lexists(path)]
    if present:
        fail("forbidden paths present: {}".format(", ".join(present)))
    print("forbidden_paths: PASS (0 present)")

    entries = list(dict.fromkeys(artifact_entries()))
    regular_files = []
    directories = 0
    for path in entries:
        mode = os.lstat(path).st_mode
        if stat.S_ISREG(mode):
            regular_files.append(path)
        elif stat.S_ISDIR(mode):
            directories += 1
        else:
            fail("non-regular artifact entry: {}".format(path))
    print(
        "file_types: PASS ({} regular files, {} directories, 0 special entries)".format(
            len(regular_files), directories
        )
    )

    try:
        learner_entries = source_inventory(".")
    except ProjectionError as error:
        fail("learner projection is invalid: {}".format(error))
    selected_roots = {path.split("/", 1)[0] for path in learner_entries}
    if selected_roots != set(LEARNER_ROOTS):
        fail("learner projection roots differ from the authoritative allowlist")
    learner_files, learner_directories = inventory_counts(learner_entries)
    print(
        "learner_projection: PASS ({} regular files, {} directories, 0 evaluator roots selected)".format(
            learner_files,
            learner_directories,
        )
    )

    parsed = {}
    for path, expected_hash in sorted(EXPECTED_CANONICAL_HASHES.items()):
        observed_hash, parsed[path] = canonical_hash(path)
        if observed_hash != expected_hash:
            fail("{} canonical value hash changed".format(path))

    manifest = parsed["MANIFEST.yaml"]
    if manifest.get("status") != "GENERATED":
        fail("manifest status is not GENERATED")
    if manifest.get("validation_labels") != ["GENERATED", "PARTIAL"]:
        fail("manifest labels are not GENERATED + PARTIAL")
    if manifest.get("productionized") is not False:
        fail("manifest productionized flag is not false")
    print("metadata_values: PASS (manifest and provenance canonical hashes)")

    findings = []
    for path in regular_files:
        with open(path, "rb") as handle:
            data = handle.read()
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(data):
                findings.append(path)
                break
    if findings:
        fail("credential-like patterns found in: {}".format(", ".join(findings)))
    print("credential_scan: PASS ({} regular files scanned)".format(len(regular_files)))


if __name__ == "__main__":
    main()
