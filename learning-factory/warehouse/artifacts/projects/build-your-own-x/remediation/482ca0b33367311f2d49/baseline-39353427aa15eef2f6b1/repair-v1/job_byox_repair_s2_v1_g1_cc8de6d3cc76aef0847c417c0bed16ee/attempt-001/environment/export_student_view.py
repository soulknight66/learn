"""Validate or export the exact learner-visible subset of a challenge pack."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path, PurePosixPath


_TOP_LEVEL_FILES = {
    "AGENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
    "MANIFEST.yaml",
    "README.md",
    "REQUIREMENTS.md",
}
_TOP_LEVEL_DIRECTORIES = {"environment", "public_tests", "starter"}
_EVALUATOR_ROOTS = {
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "VALIDATION.md",
    "adversarial",
    "benchmarks",
    "debugging",
    "review_exercises",
    "sealed",
}


class ViewError(RuntimeError):
    """The allowlist, source pack, or requested destination is unsafe."""


def _real_directory(path: Path, label: str) -> Path:
    candidate = Path(path)
    if ".." in candidate.parts:
        raise ViewError(f"{label} must not contain parent traversal")
    absolute = Path(os.path.abspath(os.fspath(candidate)))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise ViewError(f"cannot inspect {label}: {exc}") from exc
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise ViewError(f"{label} must have only real directory components")
    return absolute


def _load_paths(source: Path) -> tuple[PurePosixPath, ...]:
    allowlist = source / "environment" / "student_view_allowlist.json"
    try:
        mode = allowlist.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
            raise ViewError("student-view allowlist must be a regular file")
        document = json.loads(allowlist.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ViewError(f"cannot read student-view allowlist: {exc}") from exc
    if not isinstance(document, dict) or set(document) != {"paths", "schema_version"}:
        raise ViewError("student-view allowlist has unexpected fields")
    if document["schema_version"] != 1 or not isinstance(document["paths"], list):
        raise ViewError("student-view allowlist has an unsupported schema")
    if any(not isinstance(value, str) for value in document["paths"]):
        raise ViewError("student-view allowlist paths must be strings")
    if document["paths"] != sorted(set(document["paths"])):
        raise ViewError("student-view allowlist paths must be sorted and unique")

    paths: list[PurePosixPath] = []
    for value in document["paths"]:
        path = PurePosixPath(value)
        if (
            not value
            or value.startswith("/")
            or "\\" in value
            or path.as_posix() != value
            or any(part in ("", ".", "..") for part in path.parts)
        ):
            raise ViewError(f"unsafe allowlist path: {value!r}")
        root = path.parts[0]
        if root in _EVALUATOR_ROOTS:
            raise ViewError(f"evaluator material is forbidden from student view: {value}")
        if root not in _TOP_LEVEL_FILES and root not in _TOP_LEVEL_DIRECTORIES:
            raise ViewError(f"path is outside learner-visible roots: {value}")
        if root in _TOP_LEVEL_FILES and len(path.parts) != 1:
            raise ViewError(f"top-level learner file cannot contain descendants: {value}")
        paths.append(path)

    if set(path.as_posix() for path in paths).intersection(_EVALUATOR_ROOTS):
        raise ViewError("student-view allowlist includes an evaluator root")
    return tuple(paths)


def build_plan(source: Path) -> tuple[tuple[PurePosixPath, Path], ...]:
    """Return the checked allowlist plan without creating an output tree."""

    source = _real_directory(Path(source), "source")
    plan: list[tuple[PurePosixPath, Path]] = []
    for relative in _load_paths(source):
        candidate = source
        for part in relative.parts:
            candidate = candidate / part
            try:
                mode = candidate.lstat().st_mode
            except OSError as exc:
                raise ViewError(f"cannot inspect allowlisted path {relative}: {exc}") from exc
            if stat.S_ISLNK(mode):
                raise ViewError(f"allowlisted path traverses a symbolic link: {relative}")
        if not stat.S_ISREG(mode):
            raise ViewError(f"allowlisted path is not a regular file: {relative}")
        plan.append((relative, candidate))
    return tuple(plan)


def export_student_view(source: Path, destination: Path) -> int:
    """Copy only checked allowlisted files into one new atomically named directory."""

    plan = build_plan(source)
    source_root = _real_directory(Path(source), "source")
    destination_input = Path(destination)
    if ".." in destination_input.parts:
        raise ViewError("destination must not contain parent traversal")
    destination = Path(os.path.abspath(os.fspath(destination_input)))
    if destination.exists() or destination.is_symlink():
        raise ViewError("destination must not already exist")
    _real_directory(destination.parent, "destination parent")
    if destination.is_relative_to(source_root) or source_root.is_relative_to(destination):
        raise ViewError("source and destination must be separate trees")

    temporary = Path(tempfile.mkdtemp(prefix=".student-view-", dir=destination.parent))
    try:
        for relative, source_file in plan:
            output = temporary.joinpath(*relative.parts)
            output.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            shutil.copyfile(source_file, output)
            os.chmod(output, 0o644)
        os.rename(temporary, destination)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return len(plan)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("."))
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--destination", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.check:
            count = len(build_plan(args.source))
        else:
            count = export_student_view(args.source, args.destination)
    except ViewError as exc:
        print(str(exc).replace("\n", " "), file=sys.stderr)
        return 2
    print(json.dumps({"files": count, "status": "ok"}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
