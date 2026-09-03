#!/usr/bin/env python3
"""Deterministic packaging and hygiene checks; not a solution validator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import stat
import sys

try:
    from .export_views import ExportError, ROLE_TOP_LEVEL, verify_view
except ImportError:  # Direct execution places environment/ rather than the pack root on sys.path.
    from export_views import ExportError, ROLE_TOP_LEVEL, verify_view

ROOT = Path(__file__).resolve().parents[1]
VIEW_MANIFEST = "environment/VIEW_MANIFEST.json"
REQUIRED = (
    "AGENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "LICENSE_BOUNDARY.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "README.md",
    "REQUIREMENTS.md",
    "VALIDATION.md",
    "adversarial/README.md",
    "adversarial/test_reference_adversarial.py",
    "benchmarks/README.md",
    "benchmarks/benchmark_reference.py",
    "debugging/README.md",
    "debugging/path_escape/README.md",
    "debugging/path_escape/candidate.py",
    "debugging/path_escape/sealed/ANSWER.md",
    "debugging/path_escape/sealed/corrected.py",
    "debugging/path_escape/test_candidate.py",
    "environment/PROVENANCE.sha256",
    "environment/README.md",
    "environment/check_host.py",
    "environment/export_views.py",
    "environment/verify_pack.py",
    "public_tests/README.md",
    "public_tests/checkpoints.py",
    "public_tests/test_paths.py",
    "public_tests/test_spec.py",
    "review_exercises/README.md",
    "review_exercises/runner_review/README.md",
    "review_exercises/runner_review/candidate.py",
    "review_exercises/runner_review/sealed/ANSWER.md",
    "sealed/DESIGN.md",
    "sealed/REVIEW.md",
    "sealed/TRADEOFFS.md",
    "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md",
    "sealed/reference/README.md",
    "sealed/reference/minictr/__init__.py",
    "sealed/reference/minictr/__main__.py",
    "sealed/reference/minictr/child.py",
    "sealed/reference/minictr/cli.py",
    "sealed/reference/minictr/errors.py",
    "sealed/reference/minictr/paths.py",
    "sealed/reference/minictr/planner.py",
    "sealed/reference/minictr/preflight.py",
    "sealed/reference/minictr/registry.py",
    "sealed/reference/minictr/runner.py",
    "sealed/reference/minictr/spec.py",
    "sealed/reference_tests/README.md",
    "sealed/reference_tests/test_cli_and_preflight.py",
    "sealed/reference_tests/test_export_views.py",
    "sealed/reference_tests/test_linux_integration.py",
    "sealed/reference_tests/test_pack_verifier.py",
    "sealed/reference_tests/test_planner.py",
    "sealed/reference_tests/test_registry.py",
    "sealed/reference_tests/test_runner_and_child.py",
    "sealed/reference_tests/test_spec_and_paths.py",
    "starter/README.md",
    "starter/minictr/__init__.py",
    "starter/minictr/__main__.py",
    "starter/minictr/child.py",
    "starter/minictr/cli.py",
    "starter/minictr/errors.py",
    "starter/minictr/paths.py",
    "starter/minictr/planner.py",
    "starter/minictr/preflight.py",
    "starter/minictr/registry.py",
    "starter/minictr/runner.py",
    "starter/minictr/spec.py",
)
FORBIDDEN = [
    ".git", ".env", ".venv", "credentials.json", "secrets", "reference", "reference_tests",
    "hidden_tests", "solution", "solutions", "answers", "starter/sealed", "starter/reference",
    "starter/reference_tests", "starter/solution", "starter/solutions", "starter/answers",
    "public_tests/sealed", "public_tests/reference", "public_tests/hidden_tests",
    "environment/sealed",
]
EXPECTED_MANIFEST = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_884ee11fc61abc48b60825556299dae5",
    "provenance_sha256": "f7190ea0b5ce4b06359e84384b56d25ad265a0faf0bfdd6208378b4a17b5ca5a",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}
EXPECTED_PROVENANCE_DOCUMENT_SHA256 = (
    "1b00a500c586d122105ac591fbb0868281cb0524f989f607326e0a896d75b611"
)
SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
]


def _provenance_document_errors(root: Path) -> list[str]:
    errors: list[str] = []
    try:
        provenance_bytes = (root / "PROVENANCE.json").read_bytes()
        provenance = json.loads(provenance_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"provenance is not strict JSON: {exc}")
    else:
        if provenance.get("snapshot_sha256") != EXPECTED_MANIFEST["provenance_sha256"]:
            errors.append("provenance snapshot binding differs from manifest")
        document_digest = hashlib.sha256(provenance_bytes).hexdigest()
        if document_digest != EXPECTED_PROVENANCE_DOCUMENT_SHA256:
            errors.append("PROVENANCE.json byte digest differs from canonical document")
    expected_digest_line = f"{EXPECTED_PROVENANCE_DOCUMENT_SHA256}  PROVENANCE.json\n"
    try:
        digest_line = (root / "environment/PROVENANCE.sha256").read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"provenance document digest declaration is unreadable: {exc}")
    else:
        if digest_line != expected_digest_line:
            errors.append("provenance document digest declaration differs from canonical digest")
    return errors


def _files_under(root: Path, top_level: tuple[str, ...]) -> set[str]:
    files: set[str] = set()
    for name in top_level:
        entry = root / name
        if entry.is_file() or entry.is_symlink():
            files.add(name)
        elif entry.is_dir():
            files.update(
                path.relative_to(root).as_posix()
                for path in entry.rglob("*")
                if path.is_file() or path.is_symlink()
            )
    return files


def _archive_entry_errors(root: Path, top_level: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    for name in top_level:
        entry = root / name
        candidates = [entry]
        if entry.is_dir() and not entry.is_symlink():
            candidates.extend(entry.rglob("*"))
        for path in candidates:
            try:
                mode = path.lstat().st_mode
            except OSError as exc:
                errors.append(f"archive entry is unreadable: {path.relative_to(root)}: {exc}")
                continue
            relative = path.relative_to(root)
            if path.is_symlink() or not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                errors.append(f"non-regular archive entry: {relative}")
                continue
            if path.name == "__pycache__" or path.suffix in {".pyc", ".pyo"}:
                errors.append(f"generated bytecode entry: {relative}")
            if stat.S_ISREG(mode):
                data = path.read_bytes()
                for pattern in SECRET_PATTERNS:
                    if pattern.search(data):
                        errors.append(f"credential-like content: {relative}")
    return errors


def main() -> int:
    errors: list[str] = []
    view_manifest = ROOT / VIEW_MANIFEST
    role: str | None = None
    if view_manifest.is_file() and not view_manifest.is_symlink():
        try:
            summary = verify_view(ROOT)
            role = str(summary["role"])
        except ExportError as exc:
            errors.append(f"export view verification failed: {exc}")
    top_level = tuple(ROLE_TOP_LEVEL[role or "instructor"])
    required = {
        name for name in REQUIRED if name.partition("/")[0] in set(top_level)
    }
    if role is not None:
        required.add(VIEW_MANIFEST)
    for name in sorted(required):
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            errors.append(f"required regular file missing: {name}")
    actual_files = _files_under(ROOT, top_level)
    missing = sorted(required - actual_files)
    unexpected = sorted(actual_files - required)
    if missing:
        errors.append(f"canonical file set is missing: {', '.join(missing)}")
    if unexpected:
        errors.append(f"canonical file set has unexpected entries: {', '.join(unexpected)}")
    for name in FORBIDDEN:
        if (ROOT / name).exists() or (ROOT / name).is_symlink():
            errors.append(f"forbidden path exists: {name}")
    errors.extend(_archive_entry_errors(ROOT, top_level))
    try:
        manifest = json.loads((ROOT / "MANIFEST.yaml").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"manifest is not strict JSON: {exc}")
    else:
        if manifest != EXPECTED_MANIFEST:
            errors.append("manifest differs from authoritative object")
    if role != "learner":
        errors.extend(_provenance_document_errors(ROOT))
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    kind = role or "source"
    print(
        f"OK: {kind} pack with {len(required)} canonical files; complete file set; "
        "forbidden paths absent; regular entries only; metadata and credential scan clean"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
