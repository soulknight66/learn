#!/usr/bin/env python3
"""Deterministically verify artifact structure, metadata, and credential hygiene."""

import hashlib
import json
import os
import re


PACK_ENTRIES = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json",
    "LICENSE_BOUNDARY.md", "REQUIREMENTS.md", "CONCEPTS.md",
    "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter", "public_tests",
    "environment", "sealed", "adversarial", "debugging",
    "review_exercises", "benchmarks",
]

EXPECTED_FILES = {
    "AGENTS.md", "CONCEPTS.md", "DESIGN_QUESTIONS.md",
    "LICENSE_BOUNDARY.md", "MANIFEST.yaml", "PROVENANCE.json", "README.md",
    "REQUIREMENTS.md", "VALIDATION.md", "adversarial/README.md",
    "adversarial/run_tests.py", "benchmarks/README.md",
    "benchmarks/run_benchmark.py", "debugging/README.md",
    "environment/README.md", "environment/__init__.py",
    "environment/check_toolchain.py", "environment/process_runner.py",
    "public_tests/README.md", "public_tests/cases/arithmetic.pb",
    "public_tests/cases/control_flow.pb", "public_tests/lexer_smoke.c",
    "public_tests/run_lexer_tests.py", "public_tests/run_tests.py",
    "review_exercises/README.md", "sealed/DESIGN.md", "sealed/REVIEW.md",
    "sealed/TRADEOFFS.md", "sealed/alternatives/README.md",
    "sealed/debugging/overflow_flag/README.md",
    "sealed/debugging/overflow_flag/candidate.s",
    "sealed/debugging/overflow_flag/sealed/ANSWER.md",
    "sealed/production/PRODUCTIONIZATION.md", "sealed/reference/Makefile",
    "sealed/reference/README.md", "sealed/reference/main.c",
    "sealed/reference/pebble.c", "sealed/reference/pebble.h",
    "sealed/reference_tests/README.md",
    "sealed/reference_tests/process_tree_helper.py",
    "sealed/reference_tests/run_tests.py",
    "sealed/reference_tests/verify_artifact.py",
    "sealed/review_exercises/symbol_resolution/README.md",
    "sealed/review_exercises/symbol_resolution/candidate.c",
    "sealed/review_exercises/symbol_resolution/sealed/ANSWER.md",
    "starter/Makefile", "starter/README.md", "starter/examples/count.pb",
    "starter/include/lexer.h", "starter/include/pebble.h",
    "starter/src/lexer.c", "starter/src/main.c", "starter/src/pipeline.c",
}

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
    "benchmarks/README.md",
]

FORBIDDEN = [
    ".git", ".env", ".venv", "credentials.json", "secrets", "reference",
    "reference_tests", "hidden_tests", "solution", "solutions", "answers",
    "starter/sealed", "starter/reference", "starter/reference_tests",
    "starter/solution", "starter/solutions", "starter/answers",
    "public_tests/sealed", "public_tests/reference", "public_tests/hidden_tests",
    "environment/sealed", "ARTIFACT_INVENTORY.sha256", "LICENSE",
]

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_bd342fcec50cb8a15740cbb98e57bc1e",
    "provenance_sha256": "beab7ca9438bab1f3a572340b6c30628fccc650ddae0fd4c5de7128543427b0a",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

EXPECTED_FILE_SHA256 = {
    "MANIFEST.yaml": "ba3e84a7d6122a40394ede353841fc4d8396eff2a7adf7d4d7962bdf45711593",
    "PROVENANCE.json": "a923b5d3d1b9eddb2f2bc1fa7e93d5f28fe40ea8ef4727165ac9ad313ea0504d",
}

CREDENTIAL_PATTERNS = [
    re.compile(br"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(br"AKIA[0-9A-Z]{16}"),
    re.compile(br"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(br"sk-[A-Za-z0-9]{32,}"),
    re.compile(br"(?i)(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*"
               br"[\"'][^\"'\s]{8,}[\"']"),
]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    missing = [path for path in REQUIRED if not os.path.isfile(path)]
    forbidden = [path for path in FORBIDDEN if os.path.lexists(path)]
    special = []
    text_files = []
    credential_hits = []

    paths = []
    for entry in PACK_ENTRIES:
        if not os.path.lexists(entry):
            continue
        if os.path.islink(entry) or not (os.path.isfile(entry) or os.path.isdir(entry)):
            special.append(entry)
            continue
        if os.path.isfile(entry):
            paths.append(entry)
            continue
        for base, directories, files in os.walk(entry, followlinks=False):
            for name in directories + files:
                path = os.path.join(base, name)
                if os.path.islink(path) or not (
                        os.path.isfile(path) or os.path.isdir(path)):
                    special.append(path)
            paths.extend(os.path.join(base, name) for name in files)

    for path in paths:
        if os.path.islink(path) or not os.path.isfile(path):
            continue
        with open(path, "rb") as handle:
            data = handle.read()
        if b"\0" in data:
            continue
        text_files.append(path)
        if any(pattern.search(data) for pattern in CREDENTIAL_PATTERNS):
            credential_hits.append(path)

    observed_files = set(paths)
    missing_payload = sorted(EXPECTED_FILES - observed_files)
    unexpected_payload = sorted(observed_files - EXPECTED_FILES)

    with open("MANIFEST.yaml", encoding="utf-8") as handle:
        manifest = json.load(handle)
    with open("PROVENANCE.json", encoding="utf-8") as handle:
        provenance = json.load(handle)

    failures = []
    if missing:
        failures.append("missing required files: %r" % missing)
    if forbidden:
        failures.append("forbidden paths present: %r" % forbidden)
    if special:
        failures.append("symlinks/special files present: %r" % special)
    if missing_payload:
        failures.append("missing expected pack files: %r" % missing_payload)
    if unexpected_payload:
        failures.append("unexpected pack files: %r" % unexpected_payload)
    if credential_hits:
        failures.append("credential-like values found: %r" % credential_hits)
    if manifest != EXPECTED_MANIFEST:
        failures.append("manifest object differs from authoritative value")
    if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
        failures.append("provenance snapshot hash mismatch")
    if provenance.get("material_baseline_sha256") != (
            "92e2fb7e89b3e0acaec857b05ec88b193b1360bac7052d3d6d3fa553c16b83b1"):
        failures.append("material baseline hash mismatch")
    if manifest.get("project_id") != provenance.get("project", {}).get("project_id"):
        failures.append("project identifier mismatch")
    if manifest.get("source_id") != provenance.get("project", {}).get("source_id"):
        failures.append("source identifier mismatch")
    if manifest.get("source_commit") != provenance.get("source", {}).get("commit_hash"):
        failures.append("source commit mismatch")
    if provenance.get("license_boundary", {}).get("linked_content_copied") is not False:
        failures.append("linked_content_copied must be false")
    for path, expected in EXPECTED_FILE_SHA256.items():
        observed = sha256(path)
        if observed != expected:
            failures.append("%s sha256 mismatch: %s" % (path, observed))

    print("required regular files: %d/%d" % (len(REQUIRED) - len(missing), len(REQUIRED)))
    print("forbidden paths present: %d" % len(forbidden))
    print("symlinks or special files: %d" % len(special))
    print("expected pack files: %d/%d; unexpected: %d" %
          (len(EXPECTED_FILES) - len(missing_payload), len(EXPECTED_FILES),
           len(unexpected_payload)))
    print("credential scan: %d text files, %d high-confidence hits" %
          (len(text_files), len(credential_hits)))
    print("metadata: strict JSON, exact manifest, immutable metadata hashes verified")
    print("provenance digest target: logical snapshot identifier, not file bytes")
    print("payload inventory: delegated to factory content-addressed artifact inventory")
    if failures:
        for failure in failures:
            print("FAIL: " + failure)
        raise SystemExit(1)
    print("artifact verification: OK")


if __name__ == "__main__":
    main()
