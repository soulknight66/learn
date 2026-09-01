#!/usr/bin/env python3
"""Verify deterministic packaging boundaries without opening factory-owned paths."""

import hashlib
import json
from pathlib import Path
import re
import stat


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

AUTHORED_ROOTS = (
    "starter",
    "public_tests",
    "environment",
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
)

ROOT_FILES = (
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

# SHA-256 of sorted, compact UTF-8 JSON. These bind every key and value, not file whitespace.
EXPECTED_JSON = {
    "MANIFEST.yaml": "a6c0ad16ef85530b00a79e13f644d0275ff03a10d9efd89a1ff644fbf0090ab8",
    "PROVENANCE.json": "4f9ec0833062cad5a7546998cd50978af81b8f68c584a057bd75d59920a9a8c0",
}

CREDENTIAL_PATTERNS = {
    "private-key block": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "credential assignment": re.compile(
        r"(?i)\b(?:password|passwd|api[_ -]?key|secret|access[_ -]?token)\b"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
    "URL userinfo": re.compile(r"https?://[^/\s:@]+:[^/\s@]+@"),
}


def strict_json(path: Path) -> object:
    def reject_constant(value: str) -> object:
        raise ValueError(f"non-JSON constant {value}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit(f"missing required files: {missing}")
    present = [
        name
        for name in FORBIDDEN
        if (ROOT / name).exists() or (ROOT / name).is_symlink()
    ]
    if present:
        raise SystemExit(f"forbidden paths present: {present}")

    authored_files = [ROOT / name for name in ROOT_FILES]
    for name in AUTHORED_ROOTS:
        for path in (ROOT / name).rglob("*"):
            mode = path.lstat().st_mode
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise SystemExit(f"special or symbolic path: {path.relative_to(ROOT)}")
            if stat.S_ISREG(mode):
                authored_files.append(path)

    bad_parts = {
        "sealed",
        "reference",
        "reference_tests",
        "hidden_tests",
        "solution",
        "solutions",
        "answers",
    }
    for name in ("starter", "public_tests", "environment"):
        visible_root = ROOT / name
        for path in visible_root.rglob("*"):
            relative_parts = {part.lower() for part in path.relative_to(visible_root).parts}
            if relative_parts & bad_parts:
                raise SystemExit(f"solution-bearing learner path: {path.relative_to(ROOT)}")

    hits = []
    for path in authored_files:
        text = path.read_text(encoding="utf-8")
        for label, pattern in CREDENTIAL_PATTERNS.items():
            if pattern.search(text):
                hits.append(f"{label}:{path.relative_to(ROOT)}")
    if hits:
        raise SystemExit(f"possible credentials: {hits}")

    for name, expected in EXPECTED_JSON.items():
        actual = canonical_digest(strict_json(ROOT / name))
        if actual != expected:
            raise SystemExit(f"immutable JSON mismatch: {name}")

    print(f"required_files=PASS ({len(REQUIRED)})")
    print("forbidden_paths=PASS")
    print(f"regular_paths=PASS ({len(authored_files)} files scanned)")
    print("learner_solution_paths=PASS")
    print(f"credential_scan=PASS ({len(authored_files)} files scanned)")
    print("manifest_exact=PASS")
    print("provenance_exact=PASS")


if __name__ == "__main__":
    main()
