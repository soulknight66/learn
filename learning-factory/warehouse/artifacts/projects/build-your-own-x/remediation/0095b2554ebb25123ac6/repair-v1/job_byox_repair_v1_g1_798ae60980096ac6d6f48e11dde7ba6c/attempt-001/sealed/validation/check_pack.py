#!/usr/bin/env python3
"""Deterministic structural checks for the generated challenge pack."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]

WORKSPACE_ONLY = {
    ".agents",
    ".codex",
    ".factory-workspace",
    "JOB.md",
    "PRIOR_BUILD",
    "PRIOR_REVIEW",
}

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

CANONICAL_JSON_SHA256 = {
    "MANIFEST.yaml": "1b9528b2afdc23dd22d265e7d0d09033b9908f661bc84f82ebbc8a4fb20cbb18",
    "PROVENANCE.json": "c24359e1e81bcd65754e9fa978df2413709f99aabe63c0bb224fbcc378156217",
}

RAW_JSON_SHA256 = {
    "MANIFEST.yaml": "ea4d7db5b05bd6edfd2a9e85831707e7f4d79299cafd59c49e1a93feb931626c",
    "PROVENANCE.json": "0ef563654487305f40e29ea6aade9bcce1477b623409b1038a95848b2f995b4d",
}

LEARNER_VIEW_POLICY = {
    "allowed_entries": [
        {"access": "read-only", "kind": "file", "path": "README.md"},
        {"access": "read-only", "kind": "file", "path": "AGENTS.md"},
        {"access": "read-only", "kind": "file", "path": "MANIFEST.yaml"},
        {"access": "read-only", "kind": "file", "path": "REQUIREMENTS.md"},
        {"access": "read-only", "kind": "file", "path": "CONCEPTS.md"},
        {"access": "read-only", "kind": "file", "path": "DESIGN_QUESTIONS.md"},
        {"access": "read-write", "kind": "directory", "path": "starter"},
        {"access": "read-only", "kind": "directory", "path": "public_tests"},
        {"access": "read-only", "kind": "directory", "path": "environment"},
    ],
    "denied_prefixes": [
        "sealed",
        "adversarial",
        "debugging",
        "review_exercises",
        "benchmarks",
        "PROVENANCE.json",
        "LICENSE_BOUNDARY.md",
        "VALIDATION.md",
    ],
    "runtime_boundary": {
        "learner_mount": "/workspace",
        "source_pack_mounted": False,
    },
    "schema_version": 1,
}

LEARNER_SUITE_INPUTS = (
    "starter/types_test.go",
    "public_tests/compiler_test.go",
    "sealed/learner_tests/contract_test.go",
)
LEARNER_SUITE_SHA256 = "a3f62d3b7370066dc4e7d7aa6f9c563cad5614fcc27a573e817ded056c90b032"

CREDENTIAL_PATTERNS = {
    "private-key header": re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    "assigned secret": re.compile(
        rb"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token)"
        rb"\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
}


def fail(message: str) -> None:
    print(f"FAIL {message}")
    raise SystemExit(1)


def canonical_hash(path: Path) -> str:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def all_entries():
    entries = []
    for directory, directories, filenames in os.walk(ROOT, followlinks=False):
        base = Path(directory)
        if base == ROOT:
            directories[:] = [name for name in directories if name not in WORKSPACE_ONLY]
            filenames = [name for name in filenames if name not in WORKSPACE_ONLY]
        entries.extend(base / name for name in directories)
        entries.extend(base / name for name in filenames)
    return entries


def content_tree_hash(entries):
    """Hash substantive files; VALIDATION.md is excluded to avoid self-reference."""
    digest = hashlib.sha256()
    digest.update(b"challenge-pack-content-v1\0")
    files = [
        path for path in entries
        if path.is_file() and path.relative_to(ROOT).as_posix() != "VALIDATION.md"
    ]
    for path in sorted(files, key=lambda item: item.relative_to(ROOT).as_posix()):
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(str(len(relative)).encode("ascii") + b":" + relative)
        digest.update(str(len(data)).encode("ascii") + b":" + data)
    return digest.hexdigest(), len(files)


def canonical_json_hash(value):
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def learner_suite_hash():
    digest = hashlib.sha256()
    digest.update(b"pebble-learner-suites-v1\0")
    for name in LEARNER_SUITE_INPUTS:
        encoded_name = name.encode("utf-8")
        data = (ROOT / name).read_bytes()
        digest.update(str(len(encoded_name)).encode("ascii") + b":" + encoded_name)
        digest.update(str(len(data)).encode("ascii") + b":" + data)
    return digest.hexdigest()


def main() -> int:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        fail(f"missing required files: {missing}")
    print(f"PASS required files present: {len(REQUIRED)}")

    present = [name for name in FORBIDDEN if os.path.lexists(ROOT / name)]
    if present:
        fail(f"forbidden paths present: {present}")
    print(f"PASS forbidden paths absent: {len(FORBIDDEN)}")

    actual_top_level = {path.name for path in ROOT.iterdir() if path.name not in WORKSPACE_ONLY}
    if actual_top_level != PACK_TOP_LEVEL:
        fail(
            "unexpected top-level entries: missing={} extra={}".format(
                sorted(PACK_TOP_LEVEL - actual_top_level),
                sorted(actual_top_level - PACK_TOP_LEVEL),
            )
        )
    print(f"PASS exact pack top level: {len(PACK_TOP_LEVEL)}")

    entries = all_entries()
    special = []
    for path in entries:
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            special.append(str(path.relative_to(ROOT)))
    if special:
        fail(f"symlink or special entries present: {special}")
    file_count = sum(1 for path in entries if path.is_file())
    directory_count = sum(1 for path in entries if path.is_dir())
    empty_directories = [
        str(path.relative_to(ROOT)) for path in entries
        if path.is_dir() and not any(path.iterdir())
    ]
    if empty_directories:
        fail(f"empty directories are not archive-stable: {empty_directories}")
    print(f"PASS regular files: {file_count}; nonempty directories: {directory_count}")

    for name, expected in CANONICAL_JSON_SHA256.items():
        actual = canonical_hash(ROOT / name)
        if actual != expected:
            fail(f"canonical JSON mismatch for {name}: {actual}")
    for name, expected in RAW_JSON_SHA256.items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual != expected:
            fail(f"raw immutable JSON mismatch for {name}: {actual}")
    manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
    provenance = json.loads((ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "GENERATED" or manifest.get("validation_labels") != [
        "GENERATED",
        "PARTIAL",
    ]:
        fail("manifest status or labels changed")
    snapshot_preimage = {
        "project": provenance.get("project"),
        "source": provenance.get("source"),
    }
    snapshot_hash = canonical_json_hash(snapshot_preimage)
    if snapshot_hash != provenance.get("snapshot_sha256") or snapshot_hash != manifest.get("provenance_sha256"):
        fail(f"source snapshot hash mismatch: {snapshot_hash}")
    print("PASS immutable JSON, source-snapshot hash, and GENERATED/PARTIAL labels match")

    policy = json.loads((ROOT / "environment/learner-view.json").read_text(encoding="utf-8"))
    if policy != LEARNER_VIEW_POLICY:
        fail("learner-view policy mismatch")
    print("PASS machine-readable learner-view allowlist and runtime boundary match")

    suite_hash = learner_suite_hash()
    if suite_hash != LEARNER_SUITE_SHA256:
        fail(f"learner suite content lock mismatch: {suite_hash}")
    print(f"PASS harness-controlled learner suite content lock: {suite_hash}")

    excluded = {"JOB.md", ".factory-workspace"}
    hits = []
    scanned = 0
    for path in entries:
        if not path.is_file() or path.relative_to(ROOT).as_posix() in excluded:
            continue
        scanned += 1
        data = path.read_bytes()
        for label, pattern in CREDENTIAL_PATTERNS.items():
            if pattern.search(data):
                hits.append(f"{path.relative_to(ROOT)} ({label})")
    if hits:
        fail(f"credential-like patterns found: {hits}")
    print(f"PASS no credential-like patterns in generated files: {scanned}")
    tree_hash, hashed_files = content_tree_hash(entries)
    print(
        "PASS challenge-pack-content-v1 SHA-256 excluding VALIDATION.md: {} ({} files)".format(
            tree_hash, hashed_files
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
