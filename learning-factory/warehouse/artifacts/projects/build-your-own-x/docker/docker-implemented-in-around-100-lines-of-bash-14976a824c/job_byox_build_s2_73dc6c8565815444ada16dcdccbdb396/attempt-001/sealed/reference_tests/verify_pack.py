#!/usr/bin/env python3
"""Deterministic structural checks for this generated challenge pack."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]

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

EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_44e8061be7b19deb5e3e6b2fdef38d1a",
    "provenance_sha256": "9c1c2b2d10c1bdf898ea3e34100b636f5ae8158af2e95d32345bf8d9ea68c95d",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

EXPECTED_PROVENANCE_CANONICAL_SHA256 = (
    "7b2dac00b3a612eeeb3afa49141c02949998504331dbc852cd174d0bb32b2426"
)

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)://[^\s/:]+:[^\s/@]+@"),
    re.compile(
        r"(?i)(?:password|passwd|api[_-]?key|client[_-]?secret)"
        r"[ \t]*[:=][ \t]*['\"]?[^\s'\"]{8,}"
    ),
]


def reject_constant(value):
    raise ValueError("non-standard JSON constant: {}".format(value))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: {}".format(key))
        result[key] = value
    return result


def strict_json(path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(
            stream,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )


def canonical_digest(value):
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def material_files():
    root_files = [
        "README.md",
        "AGENTS.md",
        "MANIFEST.yaml",
        "PROVENANCE.json",
        "LICENSE_BOUNDARY.md",
        "REQUIREMENTS.md",
        "CONCEPTS.md",
        "DESIGN_QUESTIONS.md",
        "VALIDATION.md",
    ]
    for relative in root_files:
        path = ROOT / relative
        if path.exists():
            yield path
    for top_name in (
        "starter",
        "public_tests",
        "environment",
        "sealed",
        "adversarial",
        "debugging",
        "review_exercises",
        "benchmarks",
    ):
        top = ROOT / top_name
        if not top.exists():
            continue
        for directory, directory_names, file_names in os.walk(str(top)):
            directory_names.sort()
            file_names.sort()
            for file_name in file_names:
                yield Path(directory) / file_name


def main():
    errors = []

    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            errors.append("required regular file missing: {}".format(relative))

    for relative in FORBIDDEN:
        if os.path.lexists(str(ROOT / relative)):
            errors.append("forbidden path exists: {}".format(relative))

    for top_name in (
        "starter",
        "public_tests",
        "environment",
        "sealed",
        "adversarial",
        "debugging",
        "review_exercises",
        "benchmarks",
    ):
        top = ROOT / top_name
        if not top.exists():
            continue
        for directory, directory_names, file_names in os.walk(str(top)):
            for entry_name in directory_names + file_names:
                entry = Path(directory) / entry_name
                mode = entry.lstat().st_mode
                if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                    errors.append("non-regular artifact entry: {}".format(entry.relative_to(ROOT)))

    try:
        manifest = strict_json(ROOT / "MANIFEST.yaml")
        if manifest != EXPECTED_MANIFEST:
            errors.append("MANIFEST.yaml differs from its authoritative object")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors.append("MANIFEST.yaml is not strict JSON: {}".format(error))

    try:
        provenance = strict_json(ROOT / "PROVENANCE.json")
        if canonical_digest(provenance) != EXPECTED_PROVENANCE_CANONICAL_SHA256:
            errors.append("PROVENANCE.json differs from its immutable snapshot")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors.append("PROVENANCE.json is not strict JSON: {}".format(error))

    for path in material_files():
        mode = path.lstat().st_mode
        if not stat.S_ISREG(mode):
            errors.append("material file is not regular: {}".format(path.relative_to(ROOT)))
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            errors.append("cannot scan text file {}: {}".format(path.relative_to(ROOT), error))
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append("credential-like content in {}".format(path.relative_to(ROOT)))
                break

    if errors:
        for error in errors:
            print("FAIL {}".format(error))
        return 1

    print("PASS required regular files: {}".format(len(REQUIRED)))
    print("PASS forbidden paths absent: {}".format(len(FORBIDDEN)))
    print("PASS artifact entries are regular files/directories")
    print("PASS strict manifest and immutable provenance objects")
    print("PASS credential-pattern scan")
    return 0


if __name__ == "__main__":
    sys.exit(main())
