#!/usr/bin/env python3
"""Audit an orchestrator-materialized learner view against the explicit policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any

POLICY_KEYS = {
    "schema_version",
    "exposure_model",
    "root_files",
    "root_directories",
    "forbidden_path_components",
    "allowed_entry_types",
    "independent_materialization_validation",
}


class AuditError(ValueError):
    pass


def _unique_names(value: Any, location: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise AuditError(f"{location}: expected a nonempty list")
    if any(
        not isinstance(item, str)
        or not item
        or "/" in item
        or item in {".", ".."}
        for item in value
    ):
        raise AuditError(
            f"{location}: entries must be single nonempty path components"
        )
    if len(set(value)) != len(value):
        raise AuditError(f"{location}: duplicate entry")
    return value


def load_policy(path: Path) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AuditError(f"cannot load policy {path}: {error}") from error
    if not isinstance(policy, dict) or set(policy) != POLICY_KEYS:
        raise AuditError(f"policy: expected exactly {sorted(POLICY_KEYS)}")
    if policy["schema_version"] != 1:
        raise AuditError("policy.schema_version: expected 1")
    if policy["exposure_model"] != "explicit-root-allowlist":
        raise AuditError("policy.exposure_model: unexpected value")
    root_files = _unique_names(policy["root_files"], "policy.root_files")
    root_directories = _unique_names(
        policy["root_directories"], "policy.root_directories"
    )
    if set(root_files) & set(root_directories):
        raise AuditError("policy: root file/directory overlap")
    _unique_names(
        policy["forbidden_path_components"], "policy.forbidden_path_components"
    )
    if policy["allowed_entry_types"] != ["directory", "regular_file"]:
        raise AuditError("policy.allowed_entry_types: unexpected value")
    if policy["independent_materialization_validation"] != "REQUIRED":
        raise AuditError(
            "policy.independent_materialization_validation: expected REQUIRED"
        )
    return policy


def validate_top_level(
    actual: set[str], policy: dict[str, Any], strict: bool
) -> None:
    allowed = set(policy["root_files"]) | set(policy["root_directories"])
    missing = allowed - actual
    extra = actual - allowed if strict else set()
    if missing or extra:
        raise AuditError(
            f"top level mismatch: missing={sorted(missing)} extra={sorted(extra)}"
        )


def validate_relative_path(relative: str, policy: dict[str, Any]) -> None:
    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise AuditError(f"unsafe relative path: {relative!r}")
    forbidden = {
        item.casefold() for item in policy["forbidden_path_components"]
    }
    rejected = [part for part in path.parts if part.casefold() in forbidden]
    if rejected:
        raise AuditError(
            f"forbidden path component in {relative!r}: {rejected[0]!r}"
        )


def validate_inventory(
    inventory: list[dict[str, Any]], policy: dict[str, Any]
) -> None:
    root_files = set(policy["root_files"])
    root_directories = set(policy["root_directories"])
    seen: set[str] = set()
    top_level: set[str] = set()

    for entry in inventory:
        if not isinstance(entry, dict) or set(entry) != {
            "path",
            "type",
            "sha256",
        }:
            raise AuditError("inventory entry has an unexpected shape")
        relative = entry["path"]
        if not isinstance(relative, str):
            raise AuditError("inventory path is not a string")
        validate_relative_path(relative, policy)
        if relative in seen:
            raise AuditError(f"duplicate inventory path: {relative}")
        seen.add(relative)
        parts = PurePosixPath(relative).parts
        top_level.add(parts[0])
        kind = entry["type"]
        digest = entry["sha256"]
        if parts[0] in root_files:
            if len(parts) != 1 or kind != "regular_file":
                raise AuditError(f"root file has wrong shape or type: {relative}")
        elif parts[0] in root_directories:
            if len(parts) == 1 and kind != "directory":
                raise AuditError(f"root directory has wrong type: {relative}")
            if kind not in {"directory", "regular_file"}:
                raise AuditError(f"disallowed entry type at {relative}: {kind}")
        else:
            raise AuditError(f"path is not allowlisted: {relative}")
        if kind == "regular_file":
            if not isinstance(digest, str) or len(digest) != 64:
                raise AuditError(f"regular file lacks SHA-256: {relative}")
            if any(character not in "0123456789abcdef" for character in digest):
                raise AuditError(f"invalid SHA-256 at {relative}")
        elif digest is not None:
            raise AuditError(f"directory unexpectedly has a digest: {relative}")

    validate_top_level(top_level, policy, strict=True)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scan_entry(
    path: Path,
    relative: str,
    policy: dict[str, Any],
    inventory: list[dict[str, Any]],
) -> None:
    validate_relative_path(relative, policy)
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        raise AuditError(f"symbolic link is forbidden: {relative}")
    if stat.S_ISREG(mode):
        inventory.append(
            {
                "path": relative,
                "type": "regular_file",
                "sha256": _file_sha256(path),
            }
        )
        return
    if not stat.S_ISDIR(mode):
        raise AuditError(f"special filesystem object is forbidden: {relative}")
    inventory.append({"path": relative, "type": "directory", "sha256": None})
    for child in sorted(path.iterdir(), key=lambda item: item.name):
        _scan_entry(child, f"{relative}/{child.name}", policy, inventory)


def scan(
    root: Path, policy: dict[str, Any], strict: bool
) -> list[dict[str, Any]]:
    root_mode = root.lstat().st_mode
    if not stat.S_ISDIR(root_mode) or stat.S_ISLNK(root_mode):
        raise AuditError(f"audit root is not a real directory: {root}")
    actual = {entry.name for entry in root.iterdir()}
    validate_top_level(actual, policy, strict)
    selected = sorted(
        set(policy["root_files"]) | set(policy["root_directories"])
    )
    inventory: list[dict[str, Any]] = []
    for name in selected:
        _scan_entry(root / name, name, policy, inventory)
    inventory.sort(key=lambda entry: entry["path"])
    validate_inventory(inventory, policy)
    return inventory


def inventory_digest(inventory: list[dict[str, Any]]) -> str:
    encoded = json.dumps(
        inventory, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path(__file__).with_name("student_view_policy.json"),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--view", type=Path, help="strict materialized learner view")
    mode.add_argument(
        "--source-pack",
        type=Path,
        help="audit only allowlisted inputs in a full evaluator pack",
    )
    parser.add_argument("--list", action="store_true", help="include full inventory")
    args = parser.parse_args()

    try:
        policy = load_policy(args.policy)
        strict = args.view is not None
        root = args.view if strict else args.source_pack
        assert root is not None
        inventory = scan(root, policy, strict)
    except (AuditError, OSError) as error:
        print(f"student_view_audit: FAIL: {error}", file=sys.stderr)
        return 1

    result: dict[str, Any] = {
        "status": "PASS",
        "mode": "materialized-view" if strict else "allowlisted-source",
        "entries": len(inventory),
        "regular_files": sum(
            item["type"] == "regular_file" for item in inventory
        ),
        "directories": sum(item["type"] == "directory" for item in inventory),
        "inventory_sha256": inventory_digest(inventory),
    }
    if args.list:
        result["inventory"] = inventory
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
