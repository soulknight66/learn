#!/usr/bin/env python3
"""Write or verify the deterministic Minibox pack file inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile


PROJECT_ID = "project_884ee11fc61abc48b60825556299dae5"
PROVENANCE_SNAPSHOT_SHA256 = (
    "f7a36c6e3d6cae8eaefb0e013c4b9f9f9190dc2eb15a90ccdec01284edce28d2"
)
PACK_ROOTS = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "PROVENANCE.json",
    "LICENSE",
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
WORKSPACE_CONTROLS = {
    ".agents",
    ".codex",
    ".factory-workspace",
    "JOB.md",
    "PRIOR_BUILD",
    "PRIOR_REVIEW",
}
INVENTORY_RELATIVE = Path("sealed/production/ARTIFACT_INVENTORY.json")


class InventoryError(Exception):
    """The challenge pack cannot be inventoried deterministically."""


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


def _regular_files(root: Path) -> list[Path]:
    known = set(PACK_ROOTS) | WORKSPACE_CONTROLS
    unknown = sorted(path.name for path in root.iterdir() if path.name not in known)
    if unknown:
        raise InventoryError("unknown top-level entries: " + ", ".join(unknown))

    files: list[Path] = []
    for root_name in PACK_ROOTS:
        candidate = root / root_name
        try:
            metadata = os.lstat(candidate)
        except FileNotFoundError as exc:
            raise InventoryError(f"pack root is missing: {root_name}") from exc
        if stat.S_ISREG(metadata.st_mode):
            files.append(candidate)
            continue
        if not stat.S_ISDIR(metadata.st_mode):
            raise InventoryError(f"pack root has unsupported type: {root_name}")
        for entry in sorted(candidate.rglob("*"), key=lambda value: value.as_posix()):
            entry_metadata = os.lstat(entry)
            if stat.S_ISDIR(entry_metadata.st_mode):
                continue
            if not stat.S_ISREG(entry_metadata.st_mode):
                raise InventoryError(
                    f"pack entry is not a regular file or directory: "
                    f"{entry.relative_to(root).as_posix()}"
                )
            files.append(entry)
    return sorted(
        (path for path in files if path.relative_to(root) != INVENTORY_RELATIVE),
        key=lambda value: value.relative_to(root).as_posix(),
    )


def build_inventory(root: Path) -> dict[str, object]:
    root = root.resolve(strict=True)
    entries = []
    for path in _regular_files(root):
        data = path.read_bytes()
        entries.append(
            {
                "bytes": len(data),
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    manifest_data = (root / "MANIFEST.yaml").read_bytes()
    provenance_data = (root / "PROVENANCE.json").read_bytes()
    return {
        "algorithm": "sha256",
        "entries": entries,
        "excluded": [INVENTORY_RELATIVE.as_posix()],
        "manifest_sha256": hashlib.sha256(manifest_data).hexdigest(),
        "project_id": PROJECT_ID,
        "provenance_document_sha256": hashlib.sha256(provenance_data).hexdigest(),
        "provenance_snapshot_sha256": PROVENANCE_SNAPSHOT_SHA256,
        "schema_version": 1,
        "top_level_roots": list(PACK_ROOTS),
    }


def encoded_inventory(root: Path) -> bytes:
    return (
        json.dumps(build_inventory(root), indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def write_inventory(root: Path) -> tuple[int, str]:
    root = root.resolve(strict=True)
    target = root / INVENTORY_RELATIVE
    data = encoded_inventory(root)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".artifact-inventory.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_name, target)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
    return len(build_inventory(root)["entries"]), hashlib.sha256(data).hexdigest()


def verify_inventory(root: Path) -> tuple[int, str]:
    root = root.resolve(strict=True)
    target = root / INVENTORY_RELATIVE
    try:
        actual = _strict_json(target)
    except (OSError, UnicodeError, ValueError) as exc:
        raise InventoryError(f"cannot read artifact inventory: {exc}") from exc
    expected = build_inventory(root)
    if actual != expected:
        raise InventoryError("artifact inventory does not match pack contents")
    data = target.read_bytes()
    return len(expected["entries"]), hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("write", "verify"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        if args.action == "write":
            count, digest = write_inventory(args.root)
        else:
            count, digest = verify_inventory(args.root)
    except (InventoryError, OSError) as exc:
        parser.exit(1, f"artifact-inventory: {exc}\n")
    print(
        json.dumps(
            {"entries": count, "inventory_sha256": digest},
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
