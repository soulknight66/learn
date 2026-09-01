#!/usr/bin/env python3
"""Run deterministic structure, metadata, boundary, and credential checks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

try:
    from . import artifact_inventory, learner_view
except ImportError:  # Direct script execution.
    import artifact_inventory  # type: ignore[no-redef]
    import learner_view  # type: ignore[no-redef]


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
    "project_id": "project_884ee11fc61abc48b60825556299dae5",
    "provenance_sha256": (
        "f7a36c6e3d6cae8eaefb0e013c4b9f9f9190dc2eb15a90ccdec01284edce28d2"
    ),
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}
PROVENANCE_DOCUMENT_SHA256 = (
    "61d0f204e6e3a1e7647e3b6eed3a918b3a6b30ede1056213767ed030629a3cdc"
)


class AuditError(Exception):
    """One or more deterministic pack checks failed."""


def _strict_json(path: Path) -> object:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant {value!r}")

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=reject_constant,
        object_pairs_hook=reject_duplicates,
    )


def _credential_patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    private_key = "-----" + "BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    aws = "AK" + r"IA[0-9A-Z]{16}"
    github = "gh" + r"[pousr]_[A-Za-z0-9]{20,}"
    openai = "s" + r"k-[A-Za-z0-9]{20,}"
    assignment = (
        r"(?i)(?:passw(?:or)?d|api[_-]?key|access[_-]?token)"
        r"\s*[:=]\s*[\"'][^\"'\r\n]+[\"']"
    )
    return tuple(
        (name, re.compile(pattern))
        for name, pattern in (
            ("private_key_header", private_key),
            ("aws_access_key", aws),
            ("github_token", github),
            ("openai_token", openai),
            ("assigned_secret", assignment),
        )
    )


def audit(root: Path) -> dict[str, object]:
    root = root.resolve(strict=True)
    missing = [name for name in REQUIRED if not (root / name).is_file()]
    forbidden = [name for name in FORBIDDEN if (root / name).exists()]
    if missing:
        raise AuditError("required paths missing or non-regular: " + ", ".join(missing))
    if forbidden:
        raise AuditError("forbidden paths present: " + ", ".join(forbidden))

    manifest = _strict_json(root / "MANIFEST.yaml")
    if manifest != EXPECTED_MANIFEST:
        raise AuditError("MANIFEST.yaml does not equal the authoritative object")
    provenance = _strict_json(root / "PROVENANCE.json")
    provenance_bytes = (root / "PROVENANCE.json").read_bytes()
    provenance_digest = hashlib.sha256(provenance_bytes).hexdigest()
    if provenance_digest != PROVENANCE_DOCUMENT_SHA256:
        raise AuditError("PROVENANCE.json serialized bytes changed")
    if not isinstance(provenance, dict) or provenance.get("snapshot_sha256") != (
        manifest["provenance_sha256"]
    ):
        raise AuditError("provenance snapshot linkage is inconsistent")

    files = artifact_inventory._regular_files(root)
    patterns = _credential_patterns()
    credential_hits = []
    for path in files:
        text = path.read_bytes().decode("utf-8", errors="ignore")
        for name, pattern in patterns:
            if pattern.search(text):
                credential_hits.append(
                    {"path": path.relative_to(root).as_posix(), "pattern": name}
                )
    if credential_hits:
        raise AuditError("credential-like patterns found: " + repr(credential_hits))

    _, learner_report = learner_view.check(root)
    inventory_count, inventory_digest = artifact_inventory.verify_inventory(root)
    return {
        "credential_pattern_hits": [],
        "files_checked": len(files),
        "forbidden_paths_present": [],
        "inventory_entries": inventory_count,
        "inventory_sha256": inventory_digest,
        "learner_archive_sha256": learner_report["archive_sha256"],
        "learner_entries": learner_report["entries"],
        "manifest_sha256": hashlib.sha256(
            (root / "MANIFEST.yaml").read_bytes()
        ).hexdigest(),
        "provenance_document_sha256": provenance_digest,
        "required_paths_missing": [],
        "sealed_entries_selected": learner_report["sealed_entries_selected"],
        "status": manifest["status"],
        "validation_labels": manifest["validation_labels"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        report = audit(args.root)
    except (AuditError, OSError, ValueError, learner_view.LearnerViewError,
            artifact_inventory.InventoryError) as exc:
        parser.exit(1, f"pack-audit: {exc}\n")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
