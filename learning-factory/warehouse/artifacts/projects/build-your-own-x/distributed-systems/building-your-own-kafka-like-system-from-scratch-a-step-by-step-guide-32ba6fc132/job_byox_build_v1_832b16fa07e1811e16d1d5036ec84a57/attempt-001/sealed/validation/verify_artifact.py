#!/usr/bin/env python3
"""Deterministic structural checks for the generated challenge artifact."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]
CONTROL_NAMES = {".git", ".agents", ".codex", ".factory-workspace", "JOB.md"}

REQUIRED_PATHS = (
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

FORBIDDEN_ARTIFACT_PATHS = (
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

# These canonical hashes fingerprint the exact JSON objects supplied to this job.
EXPECTED_CANONICAL_HASHES = {
    "MANIFEST.yaml": "0189d1bdb1e7dc36f63c14bb6ff334a9bab5b0b182423a44a47d97a4b7a51df8",
    "PROVENANCE.json": "62094b8a14e6bcdd9deb3dd67888b4a96489872debc725ad2f96e04379168fb4",
}

HIGH_CONFIDENCE_CREDENTIAL_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(rb"(?i)\b(?:password|passwd|api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]"),
)


class ValidationError(RuntimeError):
    pass


def strict_json(path: Path) -> object:
    def pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValidationError(f"duplicate JSON key {key!r} in {path.name}")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise ValidationError(f"non-finite JSON number {value!r} in {path.name}")

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=pairs_hook,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValidationError(f"invalid strict JSON in {path.name}: {error}") from error


def canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_java_lexical_structure(paths: list[Path]) -> int:
    java_paths = [path for path in paths if path.is_file() and path.suffix == ".java"]
    opening_to_closing = {"(": ")", "[": "]", "{": "}"}
    for path in java_paths:
        source = path.read_text(encoding="utf-8")
        without_literals = re.sub(
            r"/\*.*?\*/|//[^\n]*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
            "",
            source,
            flags=re.DOTALL,
        )
        stack: list[str] = []
        for character in without_literals:
            if character in opening_to_closing:
                stack.append(character)
            elif character in opening_to_closing.values():
                if not stack or opening_to_closing[stack.pop()] != character:
                    raise ValidationError(f"unbalanced delimiter in {path.relative_to(ROOT)}")
        if stack:
            raise ValidationError(f"unclosed delimiter in {path.relative_to(ROOT)}")
        public_class = re.search(r"public\s+final\s+class\s+(\w+)", without_literals)
        if public_class is None or public_class.group(1) != path.stem:
            raise ValidationError(f"public class/filename mismatch in {path.relative_to(ROOT)}")
    return len(java_paths)


def artifact_paths() -> list[Path]:
    paths: list[Path] = []
    for directory, directory_names, file_names in os.walk(ROOT, followlinks=False):
        relative_directory = Path(directory).relative_to(ROOT)
        if relative_directory == Path("."):
            directory_names[:] = [name for name in directory_names if name not in CONTROL_NAMES]
            file_names = [name for name in file_names if name not in CONTROL_NAMES]
        for name in directory_names:
            paths.append(Path(directory, name))
        for name in file_names:
            paths.append(Path(directory, name))
    return paths


def validate() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).is_file()]
    if missing:
        raise ValidationError("missing required regular files: " + ", ".join(missing))

    forbidden = [path for path in FORBIDDEN_ARTIFACT_PATHS if (ROOT / path).exists()]
    if forbidden:
        raise ValidationError("forbidden artifact paths exist: " + ", ".join(forbidden))

    paths = artifact_paths()
    irregular: list[str] = []
    for path in paths:
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            irregular.append(str(path.relative_to(ROOT)))
    if irregular:
        raise ValidationError("non-regular artifact entries: " + ", ".join(irregular))

    for name, expected_hash in EXPECTED_CANONICAL_HASHES.items():
        actual_hash = canonical_hash(strict_json(ROOT / name))
        if actual_hash != expected_hash:
            raise ValidationError(
                f"{name} object mismatch: expected {expected_hash}, got {actual_hash}"
            )

    manifest = strict_json(ROOT / "MANIFEST.yaml")
    if not isinstance(manifest, dict):
        raise ValidationError("manifest root is not an object")
    if manifest.get("status") != "GENERATED":
        raise ValidationError("manifest status is not GENERATED")
    if manifest.get("validation_labels") != ["GENERATED", "PARTIAL"]:
        raise ValidationError("manifest labels are not exactly GENERATED, PARTIAL")

    credential_hits: list[str] = []
    for path in paths:
        if not stat.S_ISREG(path.lstat().st_mode):
            continue
        data = path.read_bytes()
        if any(pattern.search(data) for pattern in HIGH_CONFIDENCE_CREDENTIAL_PATTERNS):
            credential_hits.append(str(path.relative_to(ROOT)))
    if credential_hits:
        raise ValidationError(
            "possible credential material in: " + ", ".join(credential_hits)
        )

    build_products = [
        str(path.relative_to(ROOT))
        for path in paths
        if path.is_file() and path.suffix.lower() in {".class", ".jar", ".war"}
    ]
    if build_products:
        raise ValidationError("archived build products found: " + ", ".join(build_products))

    java_source_count = validate_java_lexical_structure(paths)

    print(f"PASS required regular files: {len(REQUIRED_PATHS)}")
    print("PASS forbidden generated artifact paths: 0")
    print("PASS artifact entry types: regular files/directories only")
    print("PASS strict manifest/provenance object fingerprints")
    print("PASS status and labels: GENERATED + PARTIAL")
    print("PASS high-confidence credential scan: 0 hits")
    print("PASS archived Java build products: 0")
    print(f"PASS Java lexical structure: {java_source_count} source files")
    if (ROOT / ".git").exists():
        print("NOTE pre-existing read-only factory control .git excluded from artifact scan")


if __name__ == "__main__":
    try:
        validate()
    except ValidationError as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
