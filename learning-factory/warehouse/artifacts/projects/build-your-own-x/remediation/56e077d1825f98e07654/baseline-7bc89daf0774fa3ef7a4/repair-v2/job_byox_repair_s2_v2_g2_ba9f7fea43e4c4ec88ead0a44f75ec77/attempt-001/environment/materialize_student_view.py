#!/usr/bin/env python3
"""Materialize one policy-selected learner stage and audit it before publish."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

import audit_student_view as audit


class MaterializationError(ValueError):
    pass


def _copy_regular_file(source: Path, destination: Path) -> None:
    mode = source.lstat().st_mode
    if not stat.S_ISREG(mode) or stat.S_ISLNK(mode):
        raise MaterializationError(f"source changed type during copy: {source}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(source, flags)
    try:
        with os.fdopen(descriptor, "rb") as input_file:
            descriptor = -1
            with destination.open("xb") as output_file:
                shutil.copyfileobj(input_file, output_file, length=65536)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    destination.chmod(0o644)


def materialize(
    source_pack: Path, destination: Path, policy_path: Path
) -> dict[str, object]:
    if os.path.lexists(destination):
        raise MaterializationError(f"destination already exists: {destination}")
    parent = destination.parent
    parent_mode = parent.lstat().st_mode
    if not stat.S_ISDIR(parent_mode) or stat.S_ISLNK(parent_mode):
        raise MaterializationError(f"destination parent is not a real directory: {parent}")

    policy = audit.load_policy(policy_path)
    source_inventory = audit.scan(source_pack, policy, strict=False)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.stage-", dir=parent))
    published = False
    try:
        for entry in sorted(
            source_inventory,
            key=lambda item: (item["path"].count("/"), item["path"]),
        ):
            relative = entry["path"]
            target = temporary / relative
            if entry["type"] == "directory":
                target.mkdir(mode=0o755)
            else:
                _copy_regular_file(source_pack / relative, target)

        materialized_inventory = audit.scan(temporary, policy, strict=True)
        if materialized_inventory != source_inventory:
            raise MaterializationError("materialized inventory differs from selected source")
        os.replace(temporary, destination)
        published = True
    finally:
        if not published and os.path.lexists(temporary):
            shutil.rmtree(temporary)

    return {
        "status": "PASS",
        "stage": policy["stage"],
        "entries": len(source_inventory),
        "inventory_sha256": audit.inventory_digest(source_inventory),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = materialize(args.source_pack, args.destination, args.policy)
    except (audit.AuditError, MaterializationError, OSError) as error:
        print(f"student_view_materializer: FAIL: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
