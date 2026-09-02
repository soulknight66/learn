#!/usr/bin/env python3
"""Create the exact allowlisted learner view from an evaluator challenge pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
from typing import Any


EXPECTED_POLICY = {
    "excluded_top_level": [
        "PROVENANCE.json",
        "LICENSE_BOUNDARY.md",
        "VALIDATION.md",
        "sealed",
        "adversarial",
        "debugging",
        "review_exercises",
        "benchmarks",
    ],
    "included_top_level": [
        "README.md",
        "AGENTS.md",
        "MANIFEST.yaml",
        "REQUIREMENTS.md",
        "CONCEPTS.md",
        "DESIGN_QUESTIONS.md",
        "starter",
        "public_tests",
        "environment",
    ],
    "path_policy": "regular-files-and-directories-only",
    "schema_version": 1,
}


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_policy(source: Path) -> dict[str, Any]:
    policy_path = source / "environment" / "learner_view.json"
    try:
        policy = json.loads(
            policy_path.read_text(encoding="utf-8"), object_pairs_hook=strict_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as failure:
        raise ValueError(f"cannot load strict learner-view policy: {failure}") from failure
    if policy != EXPECTED_POLICY:
        raise ValueError("learner-view policy does not equal the supported schema")
    return policy


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(64 * 1024):
            digest.update(block)
    return digest.hexdigest()


def inventory_node(path: Path, relative: Path, result: dict[str, str]) -> None:
    mode = path.lstat().st_mode
    name = relative.as_posix()
    if stat.S_ISREG(mode):
        result[name] = file_hash(path)
        return
    if not stat.S_ISDIR(mode):
        raise ValueError(f"non-regular projection source path: {name}")
    result[name + "/"] = "directory"
    with os.scandir(path) as entries:
        children = sorted(entries, key=lambda entry: entry.name)
    for child in children:
        inventory_node(Path(child.path), relative / child.name, result)


def source_inventory(source: Path, policy: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name in policy["included_top_level"]:
        path = source / name
        if not path.exists() and not path.is_symlink():
            raise ValueError(f"included source path is missing: {name}")
        inventory_node(path, Path(name), result)
    for name in policy["excluded_top_level"]:
        path = source / name
        if not path.exists() and not path.is_symlink():
            raise ValueError(f"expected evaluator-only source path is missing: {name}")
    return result


def copy_node(source: Path, destination: Path) -> None:
    mode = source.lstat().st_mode
    if stat.S_ISREG(mode):
        shutil.copy2(source, destination, follow_symlinks=False)
        return
    if not stat.S_ISDIR(mode):
        raise ValueError(f"source path changed type during projection: {source}")
    destination.mkdir()
    with os.scandir(source) as entries:
        children = sorted(entries, key=lambda entry: entry.name)
    for child in children:
        copy_node(Path(child.path), destination / child.name)


def create_projection(
    source: Path, destination: Path, policy: dict[str, Any], expected: dict[str, str]
) -> None:
    if destination.exists() or destination.is_symlink():
        raise ValueError("destination must not already exist")
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError("source and destination must not contain one another")

    created = False
    try:
        destination.mkdir(parents=False)
        created = True
        for name in policy["included_top_level"]:
            copy_node(source / name, destination / name)
        actual_names = sorted(path.name for path in destination.iterdir())
        if actual_names != sorted(policy["included_top_level"]):
            raise ValueError("projected top-level entries differ from the allowlist")
        actual: dict[str, str] = {}
        for name in policy["included_top_level"]:
            inventory_node(destination / name, Path(name), actual)
        if actual != expected:
            raise ValueError("projected file inventory differs from the allowlisted source")
    except BaseException:
        if created:
            shutil.rmtree(destination)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="evaluator challenge-pack root")
    parser.add_argument("destination", type=Path, nargs="?", help="new learner-view root")
    parser.add_argument(
        "--check-source",
        action="store_true",
        help="validate the policy and source without creating a learner view",
    )
    args = parser.parse_args()

    try:
        source = args.source.resolve(strict=True)
        if not source.is_dir():
            raise ValueError("source is not a directory")
        policy = load_policy(source)
        expected = source_inventory(source, policy)
        if args.check_source:
            if args.destination is not None:
                raise ValueError("--check-source does not accept a destination")
            print(
                "PASS learner-view source and policy: "
                f"{len(policy['included_top_level'])} included top-level entries, "
                f"{len(policy['excluded_top_level'])} excluded top-level entries, "
                f"{sum(value != 'directory' for value in expected.values())} regular files"
            )
            return 0
        if args.destination is None:
            raise ValueError("destination is required unless --check-source is used")
        destination = args.destination.resolve(strict=False)
        create_projection(source, destination, policy, expected)
        print(f"PASS created verified learner view: {destination}")
        return 0
    except (OSError, ValueError) as failure:
        print(f"FAIL {failure}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
