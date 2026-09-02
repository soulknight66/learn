#!/usr/bin/env python3
"""Deterministic structural audit for this repaired evaluator pack."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Iterable

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

PACK_TOP_LEVEL = {
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
}

WORKSPACE_CONTROLS = {
    ".agents",
    ".codex",
    ".factory-workspace",
    "PRIOR_BUILD",
    "PRIOR_REVIEW",
}

LEARNER_FORBIDDEN_COMPONENTS = {
    "sealed",
    "reference",
    "reference_tests",
    "hidden_tests",
    "solution",
    "solutions",
    "answers",
}

CREDENTIAL_PATTERNS = [
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(rb"AIza[0-9A-Za-z_-]{35}"),
]

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_fc8ca1dbad4baba3bd2d54dbb42c1a98",
    "provenance_sha256": "d55444ef84b1aeef97d1e7567137e1ea56d65f0afb190074a90031cf6c7e8726",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}


class AuditFailure(ValueError):
    pass


def _walk(path: Path) -> Iterable[Path]:
    yield path
    mode = path.lstat().st_mode
    if stat.S_ISDIR(mode) and not stat.S_ISLNK(mode):
        for child in sorted(path.iterdir(), key=lambda item: item.name):
            yield from _walk(child)


def _relative_files(root: Path) -> set[str]:
    result: set[str] = set()
    for name in sorted(PACK_TOP_LEVEL):
        path = root / name
        if not os.path.lexists(path):
            continue
        for entry in _walk(path):
            if stat.S_ISREG(entry.lstat().st_mode):
                result.add(entry.relative_to(root).as_posix())
    return result


def audit(root: Path) -> list[str]:
    failures: list[str] = []
    actual_top = {entry.name for entry in root.iterdir()}
    unexpected = actual_top - PACK_TOP_LEVEL - WORKSPACE_CONTROLS
    missing_top = PACK_TOP_LEVEL - actual_top
    if unexpected:
        failures.append(f"unexpected top-level entries: {sorted(unexpected)}")
    if missing_top:
        failures.append(f"missing pack top-level entries: {sorted(missing_top)}")

    missing_required = [
        name for name in REQUIRED if not (root / name).is_file()
    ]
    present_forbidden = [
        name for name in FORBIDDEN if os.path.lexists(root / name)
    ]
    if missing_required:
        failures.append(f"missing required paths: {missing_required}")
    if present_forbidden:
        failures.append(f"present forbidden paths: {present_forbidden}")
    for extra in ("LICENSE", "ARTIFACT_INVENTORY.sha256"):
        if os.path.lexists(root / extra):
            failures.append(f"forbidden packaging root exists: {extra}")

    regular_files = 0
    directories = 0
    symlinks = 0
    special = 0
    credential_matches: list[str] = []
    learner_rejections: list[str] = []
    for name in sorted(PACK_TOP_LEVEL):
        path = root / name
        if not os.path.lexists(path):
            continue
        for entry in _walk(path):
            mode = entry.lstat().st_mode
            relative = entry.relative_to(root).as_posix()
            if stat.S_ISLNK(mode):
                symlinks += 1
            elif stat.S_ISDIR(mode):
                directories += 1
            elif stat.S_ISREG(mode):
                regular_files += 1
                data = entry.read_bytes()
                if any(pattern.search(data) for pattern in CREDENTIAL_PATTERNS):
                    credential_matches.append(relative)
            else:
                special += 1
            parts = entry.relative_to(root).parts
            if parts and parts[0] in {"starter", "public_tests", "environment"}:
                if any(
                    component.casefold() in LEARNER_FORBIDDEN_COMPONENTS
                    for component in parts[1:]
                ):
                    learner_rejections.append(relative)

    if symlinks or special:
        failures.append(f"symlinks={symlinks} special={special}")
    if credential_matches:
        failures.append(f"credential-pattern matches: {credential_matches}")
    if learner_rejections:
        failures.append(f"learner forbidden components: {learner_rejections}")

    try:
        manifest = json.loads((root / "MANIFEST.yaml").read_text(encoding="utf-8"))
        provenance = json.loads(
            (root / "PROVENANCE.json").read_text(encoding="utf-8")
        )
        prior_provenance = json.loads(
            (root / "PRIOR_BUILD/PROVENANCE.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        failures.append(f"metadata parse failure: {error}")
        manifest = None
        provenance = None
        prior_provenance = None
    if manifest != EXPECTED_MANIFEST:
        failures.append("manifest does not equal the authoritative object")
    if provenance != prior_provenance:
        failures.append("provenance differs from the checksum-bound prior pack")

    prior_files = {
        path.relative_to(root / "PRIOR_BUILD").as_posix()
        for path in (root / "PRIOR_BUILD").rglob("*")
        if path.is_file()
    }
    current_files = _relative_files(root)
    omitted = prior_files - current_files
    expected_omitted = {"sealed/reference_tests/build/test_reference"}
    if omitted != expected_omitted:
        failures.append(f"unexpected omitted prior files: {sorted(omitted)}")
    added = current_files - prior_files

    observations = [
        f"required_count={len(REQUIRED)} missing={len(missing_required)}",
        f"forbidden_count={len(FORBIDDEN)} present={len(present_forbidden)}",
        f"pack_regular_files={regular_files} pack_directories={directories}",
        f"symlink_count={symlinks} special_count={special}",
        f"learner_forbidden_component_count={len(learner_rejections)}",
        "credential_scan=" + ("no_matches" if not credential_matches else "matches"),
        f"prior_paths_preserved={len(prior_files - omitted)} omitted_scratch={len(omitted)}",
        f"repair_paths_added={len(added)}",
        f"unexpected_top_level_count={len(unexpected)}",
        "metadata_exactness="
        + ("PASS" if manifest == EXPECTED_MANIFEST and provenance == prior_provenance else "FAIL"),
    ]
    if failures:
        raise AuditFailure("; ".join(failures))
    return observations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        observations = audit(args.pack_root)
    except (AuditFailure, OSError) as error:
        print(f"pack_audit: FAIL: {error}", file=sys.stderr)
        return 1
    print("pack_audit: PASS")
    for observation in observations:
        print(observation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
