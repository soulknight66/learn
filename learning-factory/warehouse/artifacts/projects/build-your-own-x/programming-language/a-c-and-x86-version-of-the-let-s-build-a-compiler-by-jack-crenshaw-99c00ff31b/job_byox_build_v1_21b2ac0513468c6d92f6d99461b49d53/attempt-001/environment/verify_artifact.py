#!/usr/bin/env python3
"""Deterministically verify archive structure and obvious credential hygiene."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[1]
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
ARTIFACT_ROOT_FILES = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "VALIDATION.md",
)
ARTIFACT_DIRECTORIES = (
    "starter",
    "public_tests",
    "environment",
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
)
EXPECTED_PROVENANCE_CANONICAL_SHA256 = (
    "89e2d6b2fddf6b8cd2a643e8f9290374bad176c3bc446ecbd23a7f9b21358808"
)


def artifact_paths():
    for relative in ARTIFACT_ROOT_FILES:
        yield ROOT / relative
    for directory in ARTIFACT_DIRECTORIES:
        base = ROOT / directory
        if not base.exists():
            continue
        for current, directories, files in os.walk(str(base), followlinks=False):
            current_path = Path(current)
            for name in directories:
                yield current_path / name
            for name in files:
                yield current_path / name


def fail(message):
    print("FAIL: {}".format(message))
    return False


def main():
    ok = True
    missing = [relative for relative in REQUIRED if not (ROOT / relative).is_file()]
    if missing:
        ok = fail("missing required paths: {}".format(", ".join(missing))) and ok
    else:
        print("required-paths: 23/23 regular files present")

    present = [relative for relative in FORBIDDEN if (ROOT / relative).exists()]
    if present:
        ok = fail("forbidden paths present: {}".format(", ".join(present))) and ok
    else:
        print("forbidden-paths: absent")

    unusual = []
    for path in artifact_paths():
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            unusual.append(str(path.relative_to(ROOT)))
    if unusual:
        ok = fail("symlinks or special files: {}".format(", ".join(unusual))) and ok
    else:
        print("symlinks-or-special-files: 0")

    learner_forbidden = []
    bad_names = {
        "sealed", "reference", "reference_tests", "hidden_tests",
        "solution", "solutions", "answers",
    }
    for base_name in ("starter", "public_tests", "environment"):
        base = ROOT / base_name
        for path in base.rglob("*"):
            if path.name in bad_names:
                learner_forbidden.append(str(path.relative_to(ROOT)))
    if learner_forbidden:
        ok = fail("forbidden learner names: {}".format(", ".join(learner_forbidden))) and ok
    else:
        print("learner-directory-forbidden-names: 0")

    with (ROOT / "MANIFEST.yaml").open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    expected_manifest = {
        "independent_validation": "REQUIRED",
        "productionized": False,
        "project_id": "project_bd342fcec50cb8a15740cbb98e57bc1e",
        "provenance_sha256": "16c1f2fa7154cfbf9531c6d77cf7024fd08511e5def5b6488d364f550056629b",
        "schema_version": 1,
        "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
        "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
        "status": "GENERATED",
        "validation_labels": ["GENERATED", "PARTIAL"],
    }
    with (ROOT / "PROVENANCE.json").open("r", encoding="utf-8") as handle:
        provenance = json.load(handle)
    canonical = json.dumps(
        provenance, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    metadata_ok = (
        manifest == expected_manifest
        and hashlib.sha256(canonical).hexdigest()
        == EXPECTED_PROVENANCE_CANONICAL_SHA256
        and provenance.get("snapshot_sha256") == manifest["provenance_sha256"]
    )
    if not metadata_ok:
        ok = fail("metadata does not match immutable expected objects") and ok
    else:
        print("metadata: strict JSON and exact expected objects")

    patterns = (
        re.compile(br"AKIA[0-9A-Z]{16}"),
        re.compile(br"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(br"gh[pousr]_[A-Za-z0-9]{20,}"),
        re.compile(br"sk-[A-Za-z0-9]{20,}"),
        re.compile(br"(?:password|passwd)\s*=\s*[^\s]+", re.IGNORECASE),
    )
    matches = []
    for path in artifact_paths():
        if not path.is_file() or path.is_symlink():
            continue
        content = path.read_bytes()
        if any(pattern.search(content) for pattern in patterns):
            matches.append(str(path.relative_to(ROOT)))
    if matches:
        ok = fail("credential-shaped content: {}".format(", ".join(matches))) and ok
    else:
        print("credential-pattern-scan: no matches")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
