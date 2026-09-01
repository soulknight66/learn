"""Reproducible structural and leak checks for the generated challenge pack."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat


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

FORBIDDEN_PATHS = (
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

GENERATED_ROOTS = (
    "starter",
    "public_tests",
    "environment",
    "sealed",
    "adversarial",
    "debugging",
    "review_exercises",
    "benchmarks",
)

MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_d76f888c329de3f5823edf9ffcbe85c3",
    "provenance_sha256": "b87d00ac1851cdd19fddde57f22c054a6b66257b6bdce4c4cbaf3c2bce3516c3",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}


def strict_json(path: Path) -> object:
    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise AssertionError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def main() -> int:
    root = Path.cwd()
    missing = [name for name in REQUIRED_PATHS if not (root / name).is_file()]
    forbidden = [name for name in FORBIDDEN_PATHS if os.path.lexists(root / name)]
    if missing or forbidden:
        raise AssertionError({"missing": missing, "forbidden": forbidden})

    manifest = strict_json(root / "MANIFEST.yaml")
    if manifest != MANIFEST:
        raise AssertionError("MANIFEST.yaml differs from the immutable expected object")
    provenance = strict_json(root / "PROVENANCE.json")
    if not isinstance(provenance, dict):
        raise AssertionError("PROVENANCE.json must contain an object")
    if set(provenance) != {
        "classification",
        "license_boundary",
        "project",
        "schema_version",
        "snapshot_sha256",
        "source",
    }:
        raise AssertionError("unexpected top-level provenance fields")
    if provenance["snapshot_sha256"] != MANIFEST["provenance_sha256"]:
        raise AssertionError("manifest/provenance snapshot mismatch")
    if provenance["project"]["project_id"] != MANIFEST["project_id"]:  # type: ignore[index]
        raise AssertionError("manifest/provenance project mismatch")
    if provenance["license_boundary"]["linked_content_copied"] is not False:  # type: ignore[index]
        raise AssertionError("license boundary does not deny linked-content copying")

    all_paths: list[Path] = []
    for name in GENERATED_ROOTS:
        generated_root = root / name
        all_paths.extend((generated_root, *generated_root.rglob("*")))
    symlinks: list[str] = []
    special: list[str] = []
    for path in all_paths:
        mode = path.lstat().st_mode
        relative = str(path.relative_to(root))
        if stat.S_ISLNK(mode):
            symlinks.append(relative)
        elif not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            special.append(relative)
    if symlinks or special:
        raise AssertionError({"symlinks": symlinks, "special": special})

    answer_paths = [path for path in all_paths if path.is_file() and path.name == "ANSWER.md"]
    if any(path.relative_to(root).parts[0] != "sealed" for path in answer_paths):
        raise AssertionError("an exercise answer exists outside the sealed tree")

    credential_patterns = (
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
        re.compile(
            r'''(?i)\b(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*['"][^'"]{8,}['"]'''
        ),
    )
    text_files = [path for path in all_paths if path.is_file()]
    text_files.extend(root / name for name in REQUIRED_PATHS if (root / name).parent == root)
    credential_hits: list[str] = []
    for path in set(text_files):
        content = path.read_text(encoding="utf-8")
        if any(pattern.search(content) for pattern in credential_patterns):
            credential_hits.append(str(path.relative_to(root)))
    if credential_hits:
        raise AssertionError({"possible_credentials": sorted(credential_hits)})

    policy_violations: list[str] = []
    python_files = sorted(path for path in text_files if path.suffix == ".py")
    for path in python_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call_name = (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else node.func.id if isinstance(node.func, ast.Name) else ""
            )
            if call_name in {"extract", "extractall"}:
                policy_violations.append(f"{path}:{node.lineno}: unsafe tar helper")
            if any(
                keyword.arg == "shell"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            ):
                policy_violations.append(f"{path}:{node.lineno}: shell=True")
    if policy_violations:
        raise AssertionError(policy_violations)

    report = {
        "answer_files_outside_sealed": 0,
        "forbidden_present": 0,
        "high_confidence_credential_hits": 0,
        "manifest_exact": True,
        "policy_violations": 0,
        "provenance_json_valid": True,
        "provenance_raw_sha256": hashlib.sha256((root / "PROVENANCE.json").read_bytes()).hexdigest(),
        "python_files_parsed": len(set(python_files)),
        "regular_only": True,
        "required_files": len(REQUIRED_PATHS),
        "symlinks": 0,
    }
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
