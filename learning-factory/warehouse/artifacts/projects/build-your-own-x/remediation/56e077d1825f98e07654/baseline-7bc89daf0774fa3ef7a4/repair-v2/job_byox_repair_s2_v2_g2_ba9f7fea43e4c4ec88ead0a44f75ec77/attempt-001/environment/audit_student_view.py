#!/usr/bin/env python3
"""Audit a staged learner view against an explicit disclosure policy."""

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
    "stage",
    "exposure_model",
    "root_files",
    "recursive_directories",
    "selected_files",
    "selected_directories",
    "forbidden_path_components",
    "allowed_entry_types",
    "independent_materialization_validation",
}


class AuditError(ValueError):
    pass


def _unique_names(value: Any, location: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "a list" if allow_empty else "a nonempty list"
        raise AuditError(f"{location}: expected {qualifier}")
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


def _unique_relative_paths(value: Any, location: str) -> list[str]:
    if not isinstance(value, list):
        raise AuditError(f"{location}: expected a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise AuditError(f"{location}: expected nonempty path strings")
        path = PurePosixPath(item)
        if (
            path.is_absolute()
            or str(path) != item
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise AuditError(f"{location}: unsafe relative path {item!r}")
        result.append(item)
    if len(set(result)) != len(result):
        raise AuditError(f"{location}: duplicate entry")
    return result


def validate_relative_path(relative: str, policy: dict[str, Any]) -> None:
    path = PurePosixPath(relative)
    if (
        path.is_absolute()
        or not path.parts
        or str(path) != relative
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


def load_policy(path: Path) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AuditError(f"cannot load policy {path}: {error}") from error
    if not isinstance(policy, dict) or set(policy) != POLICY_KEYS:
        raise AuditError(f"policy: expected exactly {sorted(POLICY_KEYS)}")
    if policy["schema_version"] != 2:
        raise AuditError("policy.schema_version: expected 2")
    if not isinstance(policy["stage"], str) or not policy["stage"]:
        raise AuditError("policy.stage: expected a nonempty string")
    if policy["exposure_model"] != "recursive-roots-with-exact-additions":
        raise AuditError("policy.exposure_model: unexpected value")

    root_files = _unique_names(policy["root_files"], "policy.root_files")
    recursive = _unique_names(
        policy["recursive_directories"], "policy.recursive_directories"
    )
    selected_files = _unique_relative_paths(
        policy["selected_files"], "policy.selected_files"
    )
    selected_directories = _unique_relative_paths(
        policy["selected_directories"], "policy.selected_directories"
    )
    forbidden = _unique_names(
        policy["forbidden_path_components"],
        "policy.forbidden_path_components",
    )

    if set(root_files) & set(recursive):
        raise AuditError("policy: root file/directory overlap")
    selected = set(selected_files) | set(selected_directories)
    if set(selected_files) & set(selected_directories):
        raise AuditError("policy: selected file/directory overlap")
    root_names = set(root_files) | set(recursive)
    if any(PurePosixPath(item).parts[0] in root_names for item in selected):
        raise AuditError("policy: exact selection overlaps a recursive root")

    selected_directory_set = set(selected_directories)
    for directory in selected_directories:
        parts = PurePosixPath(directory).parts
        if len(parts) > 1 and "/".join(parts[:-1]) not in selected_directory_set:
            raise AuditError(f"policy: missing selected parent for {directory!r}")
    for filename in selected_files:
        parts = PurePosixPath(filename).parts
        if len(parts) < 2 or "/".join(parts[:-1]) not in selected_directory_set:
            raise AuditError(f"policy: missing selected parent for {filename!r}")

    policy["forbidden_path_components"] = forbidden
    for relative in selected:
        validate_relative_path(relative, policy)
    for name in root_names:
        validate_relative_path(name, policy)

    if policy["allowed_entry_types"] != ["directory", "regular_file"]:
        raise AuditError("policy.allowed_entry_types: unexpected value")
    if policy["independent_materialization_validation"] != "REQUIRED":
        raise AuditError(
            "policy.independent_materialization_validation: expected REQUIRED"
        )
    return policy


def _required_top_level(policy: dict[str, Any]) -> set[str]:
    result = set(policy["root_files"]) | set(policy["recursive_directories"])
    for relative in policy["selected_files"] + policy["selected_directories"]:
        result.add(PurePosixPath(relative).parts[0])
    return result


def validate_top_level(
    actual: set[str], policy: dict[str, Any], strict: bool
) -> None:
    allowed = _required_top_level(policy)
    missing = allowed - actual
    extra = actual - allowed if strict else set()
    if missing or extra:
        raise AuditError(
            f"top level mismatch: missing={sorted(missing)} extra={sorted(extra)}"
        )


def _path_is_allowed(relative: str, kind: str, policy: dict[str, Any]) -> bool:
    parts = PurePosixPath(relative).parts
    if relative in policy["root_files"]:
        return kind == "regular_file"
    if parts[0] in policy["recursive_directories"]:
        return kind == "directory" if len(parts) == 1 else kind in {
            "directory",
            "regular_file",
        }
    if relative in policy["selected_directories"]:
        return kind == "directory"
    if relative in policy["selected_files"]:
        return kind == "regular_file"
    return False


def validate_inventory(
    inventory: list[dict[str, Any]], policy: dict[str, Any]
) -> None:
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
        top_level.add(PurePosixPath(relative).parts[0])

        kind = entry["type"]
        digest = entry["sha256"]
        if not _path_is_allowed(relative, kind, policy):
            raise AuditError(f"path or type is not allowlisted: {relative}")
        if kind == "regular_file":
            if not isinstance(digest, str) or len(digest) != 64:
                raise AuditError(f"regular file lacks SHA-256: {relative}")
            if any(character not in "0123456789abcdef" for character in digest):
                raise AuditError(f"invalid SHA-256 at {relative}")
        elif digest is not None:
            raise AuditError(f"directory unexpectedly has a digest: {relative}")

    required = (
        set(policy["root_files"])
        | set(policy["recursive_directories"])
        | set(policy["selected_files"])
        | set(policy["selected_directories"])
    )
    missing = required - seen
    if missing:
        raise AuditError(f"inventory lacks required paths: {sorted(missing)}")
    validate_top_level(top_level, policy, strict=True)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scan_one(
    path: Path,
    relative: str,
    policy: dict[str, Any],
    inventory: list[dict[str, Any]],
) -> bool:
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
        return False
    if not stat.S_ISDIR(mode):
        raise AuditError(f"special filesystem object is forbidden: {relative}")
    inventory.append({"path": relative, "type": "directory", "sha256": None})
    return True


def _scan_tree(
    path: Path,
    relative: str,
    policy: dict[str, Any],
    inventory: list[dict[str, Any]],
) -> None:
    if not _scan_one(path, relative, policy, inventory):
        return
    for child in sorted(path.iterdir(), key=lambda item: item.name):
        _scan_tree(child, f"{relative}/{child.name}", policy, inventory)


def scan(
    root: Path, policy: dict[str, Any], strict: bool
) -> list[dict[str, Any]]:
    root_mode = root.lstat().st_mode
    if not stat.S_ISDIR(root_mode) or stat.S_ISLNK(root_mode):
        raise AuditError(f"audit root is not a real directory: {root}")
    actual = {entry.name for entry in root.iterdir()}
    validate_top_level(actual, policy, strict)

    inventory: list[dict[str, Any]] = []
    if strict:
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            _scan_tree(child, child.name, policy, inventory)
    else:
        for name in sorted(policy["root_files"]):
            _scan_one(root / name, name, policy, inventory)
        for name in sorted(policy["recursive_directories"]):
            _scan_tree(root / name, name, policy, inventory)
        for relative in sorted(policy["selected_directories"]):
            if not _scan_one(root / relative, relative, policy, inventory):
                raise AuditError(f"selected directory is not a directory: {relative}")
        for relative in sorted(policy["selected_files"]):
            if _scan_one(root / relative, relative, policy, inventory):
                raise AuditError(f"selected file is not a regular file: {relative}")

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
        help="audit only policy-selected inputs in a full evaluator pack",
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
        "stage": policy["stage"],
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
