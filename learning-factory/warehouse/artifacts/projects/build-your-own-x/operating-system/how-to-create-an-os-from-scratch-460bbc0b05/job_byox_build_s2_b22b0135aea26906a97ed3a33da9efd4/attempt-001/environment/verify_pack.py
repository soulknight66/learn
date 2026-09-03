"""Deterministic structural and secret-shape checks for this generated pack."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parent.parent

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

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_9f93e5b30db7d5e4adf5244cd9ccb1b0",
    "provenance_sha256": "cd887247599d1200896aeb7cfb934318c6e53932e89be8bb7fbc18785fc1643a",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

# SHA-256 of sorted, separator-minimized JSON for the immutable provenance object.
EXPECTED_PROVENANCE_CANONICAL_SHA256 = (
    "3a63c214aa56565c201a800f6c96425588bd25768e91224a6ef7283667eadc4c"
)

GENERATED_TOP_LEVEL = (
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
)


def canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generated_files() -> list[Path]:
    files: list[Path] = []
    for relative in GENERATED_TOP_LEVEL:
        candidate = ROOT / relative
        if candidate.is_file():
            files.append(candidate)
            continue
        if candidate.is_dir():
            for directory, directory_names, file_names in os.walk(candidate):
                directory_names.sort()
                file_names.sort()
                for name in file_names:
                    files.append(Path(directory) / name)
    return files


def verify_types() -> None:
    for relative in GENERATED_TOP_LEVEL:
        top = ROOT / relative
        if top.is_symlink():
            raise AssertionError(f"generated symlink: {top.relative_to(ROOT)}")
        if top.is_file():
            continue
        for directory, directory_names, file_names in os.walk(top):
            for name in directory_names + file_names:
                path = Path(directory) / name
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                    raise AssertionError(f"non-regular archive entry: {path.relative_to(ROOT)}")


def verify_credentials(files: list[Path]) -> int:
    patterns = (
        re.compile("BEGIN " + "(?:RSA |EC |OPENSSH )?PRIVATE KEY"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"gh[opusr]_[A-Za-z0-9]{30,}"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
        re.compile(
            r"(?i)(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
        ),
    )
    scanned = 0
    for path in files:
        if "build" in path.relative_to(ROOT).parts:
            continue
        raw = path.read_bytes()
        if b"\0" in raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        for pattern in patterns:
            if pattern.search(text):
                raise AssertionError(f"credential-shaped value in {path.relative_to(ROOT)}")
    return scanned


def main() -> int:
    missing = [relative for relative in REQUIRED if not (ROOT / relative).is_file()]
    if missing:
        raise AssertionError(f"missing required regular files: {missing}")
    present_forbidden = [relative for relative in FORBIDDEN if (ROOT / relative).exists()]
    if present_forbidden:
        raise AssertionError(f"forbidden paths exist: {present_forbidden}")

    manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
    provenance = json.loads((ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
    if manifest != EXPECTED_MANIFEST:
        raise AssertionError("manifest differs from the authoritative object")
    if canonical_digest(provenance) != EXPECTED_PROVENANCE_CANONICAL_SHA256:
        raise AssertionError("provenance differs from the immutable snapshot")

    verify_types()
    files = generated_files()
    scanned = verify_credentials(files)
    print(f"required paths: {len(REQUIRED)} present regular files")
    print(f"forbidden paths: {len(FORBIDDEN)} absent")
    print("metadata: manifest and provenance match authoritative objects")
    print(f"archive entries: {len(files)} generated files; regular files/directories only")
    print(f"credential scan: {scanned} UTF-8 text files; no credential-shaped values")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
