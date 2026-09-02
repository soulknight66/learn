#!/usr/bin/env python3
"""Deterministic current-pack audit with an optional bound prior comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any, Iterable

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

PRIOR_RECORD_KEYS = {
    "schema_version",
    "source_job_id",
    "artifact_id",
    "artifact_checksum",
    "artifact_checksum_algorithm",
    "content_digest_algorithm",
    "content_sha256",
}
CONTENT_DIGEST_ALGORITHM = "canonical-path-content-sha256-v1"
CONTENT_DIGEST_DOMAIN = b"learning-factory-pack-content-v1\0"
EXPECTED_PRIOR_ARTIFACT = {
    "schema_version": 1,
    "source_job_id": "job_byox_repair_s2_v1_g1_fb171607508a433f846766f8d3726b84",
    "artifact_id": "artifact_755bc46827c04cb98a7d273da7cef9a9",
    "artifact_checksum": "90e76bbf81bf98e575baa0568818e39c78f732dcd62a7dfd7cb9c8e2f7c6cf20",
    "artifact_checksum_algorithm": "tree-sha256-v2",
}


class AuditFailure(ValueError):
    pass


def _walk(path: Path) -> Iterable[Path]:
    yield path
    mode = path.lstat().st_mode
    if stat.S_ISDIR(mode) and not stat.S_ISLNK(mode):
        for child in sorted(path.iterdir(), key=lambda item: item.name):
            yield from _walk(child)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_files(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in sorted(PACK_TOP_LEVEL):
        path = root / name
        if not os.path.lexists(path):
            continue
        for entry in _walk(path):
            if stat.S_ISREG(entry.lstat().st_mode):
                result[entry.relative_to(root).as_posix()] = _file_sha256(entry)
    return result


def _relative_directories(root: Path) -> set[str]:
    result: set[str] = set()
    for name in sorted(PACK_TOP_LEVEL):
        path = root / name
        if not os.path.lexists(path):
            continue
        for entry in _walk(path):
            if stat.S_ISDIR(entry.lstat().st_mode):
                result.add(entry.relative_to(root).as_posix())
    return result


def _load_json(path: Path, label: str, failures: list[str]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        failures.append(f"{label} parse failure: {error}")
        return None


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_current_provenance(
    provenance: Any, manifest: Any, failures: list[str]
) -> bool:
    if not isinstance(provenance, dict):
        if provenance is not None:
            failures.append("provenance root is not an object")
        return False
    try:
        project = provenance["project"]
        source = provenance["source"]
        license_boundary = provenance["license_boundary"]
        checks = {
            "schema_version": provenance["schema_version"] == 1,
            "snapshot_sha256": (
                isinstance(manifest, dict)
                and provenance["snapshot_sha256"] == manifest["provenance_sha256"]
            ),
            "project_id": (
                isinstance(manifest, dict)
                and project["project_id"] == manifest["project_id"]
            ),
            "source_id": (
                isinstance(manifest, dict)
                and source["source_id"] == manifest["source_id"]
            ),
            "source_commit": (
                isinstance(manifest, dict)
                and source["commit_hash"] == manifest["source_commit"]
            ),
            "linked_content_copied": license_boundary["linked_content_copied"] is False,
            "linked_resource_license": (
                license_boundary["linked_resource_license"] == "NOASSERTION"
            ),
        }
    except (KeyError, TypeError):
        failures.append("provenance lacks required consistency fields")
        return False
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        failures.append(f"provenance consistency failures: {failed}")
        return False
    return True


def content_inventory(root: Path) -> list[dict[str, Any]]:
    mode = root.lstat().st_mode
    if not stat.S_ISDIR(mode) or stat.S_ISLNK(mode):
        raise AuditFailure(f"content root is not a real directory: {root}")
    inventory: list[dict[str, Any]] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        for entry in _walk(child):
            relative = entry.relative_to(root).as_posix()
            entry_mode = entry.lstat().st_mode
            if stat.S_ISLNK(entry_mode):
                raise AuditFailure(f"prior content contains a symlink: {relative}")
            if stat.S_ISDIR(entry_mode):
                inventory.append({"path": relative, "type": "directory"})
            elif stat.S_ISREG(entry_mode):
                inventory.append(
                    {
                        "path": relative,
                        "type": "regular_file",
                        "size": entry.lstat().st_size,
                        "sha256": _file_sha256(entry),
                    }
                )
            else:
                raise AuditFailure(f"prior content contains a special object: {relative}")
    inventory.sort(key=lambda item: item["path"])
    return inventory


def content_digest(root: Path) -> str:
    encoded = json.dumps(
        content_inventory(root),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    digest = hashlib.sha256()
    digest.update(CONTENT_DIGEST_DOMAIN)
    digest.update(encoded)
    return digest.hexdigest()


def _audit_prior(
    root: Path,
    prior_root: Path,
    prior_record_path: Path,
    current_provenance: Any,
    failures: list[str],
) -> list[str]:
    record = _load_json(prior_record_path, "prior record", failures)
    record_valid = isinstance(record, dict) and set(record) == PRIOR_RECORD_KEYS
    if record is not None and not record_valid:
        failures.append(f"prior record must contain exactly {sorted(PRIOR_RECORD_KEYS)}")
    if record_valid:
        assert isinstance(record, dict)
        mismatched_artifact_fields = sorted(
            field
            for field, expected in EXPECTED_PRIOR_ARTIFACT.items()
            if record[field] != expected
        )
        if mismatched_artifact_fields:
            failures.append(
                "prior record artifact metadata mismatch: "
                f"{mismatched_artifact_fields}"
            )
        if record["content_digest_algorithm"] != CONTENT_DIGEST_ALGORITHM:
            failures.append("prior record content digest algorithm is unsupported")
        for field in ("artifact_checksum", "content_sha256"):
            if not _is_sha256(record[field]):
                failures.append(f"prior record {field} is not a lowercase SHA-256")
        for field in (
            "source_job_id",
            "artifact_id",
            "artifact_checksum_algorithm",
        ):
            if not isinstance(record[field], str) or not record[field]:
                failures.append(f"prior record {field} must be a nonempty string")

    try:
        prior_inventory = content_inventory(prior_root)
        observed_digest = content_digest(prior_root)
    except (AuditFailure, OSError) as error:
        failures.append(f"prior content failure: {error}")
        prior_inventory = []
        observed_digest = "UNAVAILABLE"

    if record_valid and observed_digest != record["content_sha256"]:
        failures.append(
            "prior content digest mismatch: "
            f"expected={record['content_sha256']} observed={observed_digest}"
        )

    prior_top = {item["path"].split("/", 1)[0] for item in prior_inventory}
    if prior_inventory and prior_top != PACK_TOP_LEVEL:
        failures.append(
            "prior top-level mismatch: "
            f"missing={sorted(PACK_TOP_LEVEL - prior_top)} "
            f"extra={sorted(prior_top - PACK_TOP_LEVEL)}"
        )

    prior_files = {
        item["path"]: item["sha256"]
        for item in prior_inventory
        if item["type"] == "regular_file"
    }
    current_files = _relative_files(root)
    prior_directories = {
        item["path"] for item in prior_inventory if item["type"] == "directory"
    }
    current_directories = _relative_directories(root)
    omitted = set(prior_files) - set(current_files)
    omitted_directories = prior_directories - current_directories
    if omitted:
        failures.append(f"prior files omitted from repaired pack: {sorted(omitted)}")
    if omitted_directories:
        failures.append(
            "prior directories omitted from repaired pack: "
            f"{sorted(omitted_directories)}"
        )
    added = set(current_files) - set(prior_files)
    modified = {
        path
        for path in set(prior_files) & set(current_files)
        if prior_files[path] != current_files[path]
    }

    prior_provenance = _load_json(
        prior_root / "PROVENANCE.json", "prior provenance", failures
    )
    if prior_provenance is not None and current_provenance is not None:
        if prior_provenance != current_provenance:
            failures.append("current provenance differs from the bound prior pack")

    artifact_checksum = (
        record["artifact_checksum"] if record_valid else "UNAVAILABLE"
    )
    return [
        "historical_comparison=PERFORMED",
        f"prior_content_sha256={observed_digest}",
        f"prior_artifact_checksum_recorded={artifact_checksum}",
        f"prior_regular_files={len(prior_files)}",
        f"prior_files_omitted={len(omitted)}",
        f"prior_directories={len(prior_directories)}",
        f"prior_directories_omitted={len(omitted_directories)}",
        f"repair_files_added={len(added)}",
        f"prior_files_modified={len(modified)}",
    ]


def audit(
    root: Path,
    *,
    prior_root: Path | None = None,
    prior_record: Path | None = None,
) -> list[str]:
    failures: list[str] = []
    root_mode = root.lstat().st_mode
    if not stat.S_ISDIR(root_mode) or stat.S_ISLNK(root_mode):
        raise AuditFailure(f"pack root is not a real directory: {root}")
    actual_top = {entry.name for entry in root.iterdir()}
    unexpected = actual_top - PACK_TOP_LEVEL - WORKSPACE_CONTROLS
    missing_top = PACK_TOP_LEVEL - actual_top
    if unexpected:
        failures.append(f"unexpected top-level entries: {sorted(unexpected)}")
    if missing_top:
        failures.append(f"missing pack top-level entries: {sorted(missing_top)}")

    missing_required = [name for name in REQUIRED if not (root / name).is_file()]
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
    inodes: dict[tuple[int, int], list[str]] = {}
    for name in sorted(PACK_TOP_LEVEL):
        path = root / name
        if not os.path.lexists(path):
            continue
        for entry in _walk(path):
            entry_stat = entry.lstat()
            mode = entry_stat.st_mode
            relative = entry.relative_to(root).as_posix()
            if stat.S_ISLNK(mode):
                symlinks += 1
            elif stat.S_ISDIR(mode):
                directories += 1
            elif stat.S_ISREG(mode):
                regular_files += 1
                inodes.setdefault((entry_stat.st_dev, entry_stat.st_ino), []).append(relative)
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

    hard_links = [paths for paths in inodes.values() if len(paths) > 1]
    if symlinks or special:
        failures.append(f"symlinks={symlinks} special={special}")
    if hard_links:
        failures.append(f"hard-linked pack files: {hard_links}")
    if credential_matches:
        failures.append(f"credential-pattern matches: {credential_matches}")
    if learner_rejections:
        failures.append(f"learner forbidden components: {learner_rejections}")

    manifest = _load_json(root / "MANIFEST.yaml", "manifest", failures)
    provenance = _load_json(root / "PROVENANCE.json", "provenance", failures)
    manifest_exact = manifest == EXPECTED_MANIFEST
    if manifest is not None and not manifest_exact:
        failures.append("manifest does not equal the authoritative object")
    provenance_consistent = _validate_current_provenance(
        provenance, manifest, failures
    )

    observations = [
        f"required_count={len(REQUIRED)} missing={len(missing_required)}",
        f"forbidden_count={len(FORBIDDEN)} present={len(present_forbidden)}",
        f"pack_regular_files={regular_files} pack_directories={directories}",
        f"symlink_count={symlinks} special_count={special} hard_link_groups={len(hard_links)}",
        f"learner_forbidden_component_count={len(learner_rejections)}",
        "credential_scan=" + ("no_matches" if not credential_matches else "matches"),
        f"unexpected_top_level_count={len(unexpected)}",
        "manifest_exactness=" + ("PASS" if manifest_exact else "FAIL"),
        "provenance_consistency=" + ("PASS" if provenance_consistent else "FAIL"),
    ]

    if (prior_root is None) != (prior_record is None):
        failures.append("--prior-root and --prior-record must be supplied together")
    elif prior_root is None:
        observations.append("historical_comparison=SKIPPED(no prior input)")
    else:
        assert prior_record is not None
        observations.extend(
            _audit_prior(root, prior_root, prior_record, provenance, failures)
        )

    if failures:
        raise AuditFailure("; ".join(failures))
    return observations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-root", type=Path, required=True)
    parser.add_argument(
        "--prior-root",
        type=Path,
        help="external checksum-bound prior pack for historical comparison",
    )
    parser.add_argument(
        "--prior-record",
        type=Path,
        help="sealed artifact and local-content digest record for --prior-root",
    )
    args = parser.parse_args()
    try:
        observations = audit(
            args.pack_root,
            prior_root=args.prior_root,
            prior_record=args.prior_record,
        )
    except (AuditFailure, OSError) as error:
        print(f"pack_audit: FAIL: {error}", file=sys.stderr)
        return 1
    print("pack_audit: PASS")
    for observation in observations:
        print(observation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
