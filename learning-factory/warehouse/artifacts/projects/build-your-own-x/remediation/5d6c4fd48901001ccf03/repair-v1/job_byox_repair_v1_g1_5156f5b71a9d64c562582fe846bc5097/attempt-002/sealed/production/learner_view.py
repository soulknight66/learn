#!/usr/bin/env python3
"""Build or check the deterministic, sealed-free Minibox learner archive."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tarfile
from typing import Iterable


PROJECT_ID = "project_884ee11fc61abc48b60825556299dae5"
PROVENANCE_SNAPSHOT_SHA256 = (
    "f7a36c6e3d6cae8eaefb0e013c4b9f9f9190dc2eb15a90ccdec01284edce28d2"
)
MANIFEST_SHA256 = (
    "cf665f0c237cb6320076e93c64b5419bfcb771e93f61a4054173fca30738ffab"
)
INCLUDE = (
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "starter",
    "public_tests",
    "environment",
)
MAX_VIEW_FILE_BYTES = 4 * 1024 * 1024
MAX_VIEW_TOTAL_BYTES = 16 * 1024 * 1024
POLICY_PATH = Path(__file__).with_name("LEARNER_VIEW.json")


class LearnerViewError(Exception):
    """The source tree cannot be safely packaged as a learner view."""


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


def expected_policy() -> dict[str, object]:
    return {
        "archive_format": "ustar",
        "include": list(INCLUDE),
        "manifest_sha256": MANIFEST_SHA256,
        "project_id": PROJECT_ID,
        "provenance_snapshot_sha256": PROVENANCE_SNAPSHOT_SHA256,
        "schema_version": 1,
    }


def load_policy(path: Path = POLICY_PATH) -> dict[str, object]:
    try:
        policy = _strict_json(path)
    except (OSError, UnicodeError, ValueError) as exc:
        raise LearnerViewError(f"cannot load learner-view policy: {exc}") from exc
    if policy != expected_policy():
        raise LearnerViewError("learner-view policy does not match enforced policy")
    return policy


def _kind(path: Path) -> str:
    metadata = os.lstat(path)
    if stat.S_ISREG(metadata.st_mode):
        return "file"
    if stat.S_ISDIR(metadata.st_mode):
        return "directory"
    raise LearnerViewError(f"view entry is not a regular file or directory: {path}")


def collect_entries(source: Path) -> tuple[tuple[str, Path, str], ...]:
    source = source.resolve(strict=True)
    if _kind(source) != "directory":
        raise LearnerViewError("source root is not a real directory")
    manifest = source / "MANIFEST.yaml"
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != MANIFEST_SHA256:
        raise LearnerViewError("source manifest does not match the bound manifest")

    entries: list[tuple[str, Path, str]] = []
    total_bytes = 0
    for root_name in INCLUDE:
        root = source / root_name
        try:
            root_kind = _kind(root)
        except FileNotFoundError as exc:
            raise LearnerViewError(f"required learner entry is missing: {root_name}") from exc
        entries.append((root_name, root, root_kind))
        if root_kind == "file":
            size = os.lstat(root).st_size
            if size > MAX_VIEW_FILE_BYTES:
                raise LearnerViewError(f"learner file is too large: {root_name}")
            total_bytes += size
            continue
        for candidate in sorted(root.rglob("*"), key=lambda value: value.as_posix()):
            relative = candidate.relative_to(source).as_posix()
            candidate_kind = _kind(candidate)
            entries.append((relative, candidate, candidate_kind))
            if candidate_kind == "file":
                size = os.lstat(candidate).st_size
                if size > MAX_VIEW_FILE_BYTES:
                    raise LearnerViewError(f"learner file is too large: {relative}")
                total_bytes += size
    if total_bytes > MAX_VIEW_TOTAL_BYTES:
        raise LearnerViewError("learner view exceeds its total byte limit")
    if any(name == "sealed" or name.startswith("sealed/") for name, _, _ in entries):
        raise LearnerViewError("sealed material entered the learner selection")
    return tuple(entries)


def _tar_info(name: str, kind: str, size: int = 0) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name + ("/" if kind == "directory" else ""))
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mode = 0o755 if kind == "directory" else 0o644
    info.size = size
    info.type = tarfile.DIRTYPE if kind == "directory" else tarfile.REGTYPE
    return info


def archive_bytes(entries: Iterable[tuple[str, Path, str]]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, path, kind in entries:
            if kind == "directory":
                archive.addfile(_tar_info(name, kind))
                continue
            data = path.read_bytes()
            archive.addfile(_tar_info(name, kind, len(data)), io.BytesIO(data))
    return output.getvalue()


def sealed_source_entry_count(source: Path) -> int:
    sealed = source / "sealed"
    if not sealed.exists():
        return 0
    return sum(1 for _ in sealed.rglob("*")) + 1


def check(source: Path) -> tuple[bytes, dict[str, object]]:
    load_policy()
    entries = collect_entries(source)
    data = archive_bytes(entries)
    names = [name for name, _, _ in entries]
    sealed_selected = [
        name for name in names if name == "sealed" or name.startswith("sealed/")
    ]
    if sealed_selected:
        raise LearnerViewError("sealed material entered the archive")
    report: dict[str, object] = {
        "archive_bytes": len(data),
        "archive_sha256": hashlib.sha256(data).hexdigest(),
        "entries": len(entries),
        "manifest_sha256": MANIFEST_SHA256,
        "project_id": PROJECT_ID,
        "sealed_entries_selected": 0,
        "sealed_source_entries_scanned": sealed_source_entry_count(source.resolve()),
    }
    return data, report


def _write_exclusive(path: Path, data: bytes) -> None:
    path = path.resolve(strict=False)
    with path.open("xb") as destination:
        destination.write(data)
        destination.flush()
        os.fsync(destination.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        help="write a new deterministic tar file; refuses to overwrite",
    )
    args = parser.parse_args()
    try:
        data, report = check(args.source)
        if args.output is not None:
            _write_exclusive(args.output, data)
            report["output"] = str(args.output)
    except (LearnerViewError, OSError, tarfile.TarError) as exc:
        parser.exit(1, f"learner-view: {exc}\n")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
