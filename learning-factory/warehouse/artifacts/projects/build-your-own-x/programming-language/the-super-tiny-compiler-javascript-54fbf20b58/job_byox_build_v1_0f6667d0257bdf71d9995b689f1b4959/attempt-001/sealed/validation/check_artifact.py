#!/usr/bin/env python3
"""Deterministic static checks for the generated Pebble artifact."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat


ROOT = Path(__file__).resolve().parents[2]

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

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_77599834cfe38f15a3b1a4564b1c5efb",
    "provenance_sha256": "00bc64fe9c7ff9aa00d3cda481ae335aecc762d40e03a60621342cc1eaf41fed",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

# Hashes of sorted, whitespace-independent JSON for the immutable objects supplied to this job.
EXPECTED_CANONICAL_SHA256 = {
    "MANIFEST.yaml": "4a859f7ef29b82262ab14d0905a229ac405caa20c09a87c02d96bdb2e9889abb",
    "PROVENANCE.json": "0662131d16852680e77c8aaac5c7ec76fefe6aa84c6d9373cbc196d327d66161",
}


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_strict_json(relative: str) -> object:
    return json.loads(
        (ROOT / relative).read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def artifact_files() -> list[Path]:
    files = [ROOT / name for name in REQUIRED if "/" not in name]
    for directory in ARTIFACT_DIRECTORIES:
        files.extend(path for path in (ROOT / directory).rglob("*") if path.is_file())
    return sorted(set(files))


def check_structure() -> tuple[list[str], list[str]]:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        raise AssertionError(f"missing required paths: {missing}")

    raw_forbidden = [
        name
        for name in FORBIDDEN
        if (ROOT / name).exists() or (ROOT / name).is_symlink()
    ]
    # `.git` is an injected, read-only workspace control directory. It is not part of
    # the generated artifact roots, but report it so this exception is never hidden.
    archive_forbidden = [name for name in raw_forbidden if name != ".git"]
    if archive_forbidden:
        raise AssertionError(f"forbidden artifact paths: {archive_forbidden}")

    invalid_types: list[str] = []
    root_files = [ROOT / name for name in REQUIRED if "/" not in name]
    for path in root_files:
        if not stat.S_ISREG(path.lstat().st_mode):
            invalid_types.append(str(path.relative_to(ROOT)))
    for relative in ARTIFACT_DIRECTORIES:
        for directory, dirnames, filenames in os.walk(ROOT / relative, followlinks=False):
            for name in [*dirnames, *filenames]:
                path = Path(directory) / name
                mode = path.lstat().st_mode
                if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                    invalid_types.append(str(path.relative_to(ROOT)))
    if invalid_types:
        raise AssertionError(f"symlink or special artifact paths: {invalid_types}")
    return raw_forbidden, archive_forbidden


def check_metadata() -> None:
    parsed = {
        name: load_strict_json(name)
        for name in (
            "MANIFEST.yaml",
            "PROVENANCE.json",
            "starter/package.json",
            "sealed/reference/package.json",
        )
    }
    if parsed["MANIFEST.yaml"] != EXPECTED_MANIFEST:
        raise AssertionError("MANIFEST.yaml differs from the supplied object")
    for name, expected in EXPECTED_CANONICAL_SHA256.items():
        actual = canonical_sha256(parsed[name])
        if actual != expected:
            raise AssertionError(f"{name} immutable object hash differs: {actual}")


def check_imports_and_execution_boundaries() -> tuple[int, int]:
    source_files = sorted(
        path
        for path in artifact_files()
        if path.suffix in {".js", ".mjs"}
    )
    import_pattern = re.compile(r"\bfrom\s+[\"']([^\"']+)[\"']")
    forbidden_code = re.compile(
        r"\beval\s*\(|\bFunction\s*\(|node:vm|node:child_process|child_process"
    )
    import_count = 0
    missing: list[tuple[str, str]] = []
    boundary_hits: list[str] = []
    for path in source_files:
        text = path.read_text(encoding="utf-8")
        if forbidden_code.search(text):
            boundary_hits.append(str(path.relative_to(ROOT)))
        for specifier in import_pattern.findall(text):
            if not specifier.startswith("."):
                continue
            import_count += 1
            target = (path.parent / specifier).resolve()
            if not target.is_file():
                missing.append((str(path.relative_to(ROOT)), specifier))
    if missing:
        raise AssertionError(f"missing relative imports: {missing}")
    if boundary_hits:
        raise AssertionError(f"forbidden execution mechanisms: {boundary_hits}")
    return len(source_files), import_count


def check_credentials(files: list[Path]) -> None:
    patterns = {
        "private_key": re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
        ),
        "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
        "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        "openai_style_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
        "assigned_secret": re.compile(
            r"\b(?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token)"
            r"\b\s*[:=]\s*[\"'][^\"'\n]{4,}[\"']",
            re.IGNORECASE,
        ),
    }
    hits: list[tuple[str, str]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        for label, pattern in patterns.items():
            if pattern.search(text):
                hits.append((str(path.relative_to(ROOT)), label))
    if hits:
        raise AssertionError(f"high-confidence credential patterns: {hits}")


def main() -> None:
    raw_forbidden, archive_forbidden = check_structure()
    check_metadata()
    javascript_files, relative_imports = check_imports_and_execution_boundaries()
    files = artifact_files()
    check_credentials(files)
    print(f"required paths: {len(REQUIRED)}/23 present")
    print(f"raw forbidden paths present: {raw_forbidden}")
    print(f"artifact forbidden paths present: {archive_forbidden}")
    print("artifact path types: regular files/directories only")
    print("metadata: strict JSON, exact manifest, immutable object hashes match")
    print(
        f"JavaScript modules: {javascript_files} files, "
        f"{relative_imports} relative imports resolved"
    )
    print(f"credential scan: {len(files)} files, 0 high-confidence matches")
    print("STATIC VALIDATION PASS")


if __name__ == "__main__":
    main()
