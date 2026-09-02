"""Deterministically materialize the learner-visible subset of this pack."""

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import sys
import tempfile


LEARNER_TOP_LEVEL = (
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

_DIRECTORY_TOP_LEVEL = frozenset(("starter", "public_tests", "environment"))
_FORBIDDEN_COMPONENTS = frozenset(
    (
        ".git",
        ".env",
        ".venv",
        "credentials.json",
        "secrets",
        "sealed",
        "reference",
        "reference_tests",
        "hidden_tests",
        "solution",
        "solutions",
        "answers",
    )
)
_IGNORED_NAMES = frozenset(("__pycache__", ".pytest_cache", ".mypy_cache", ".DS_Store"))
_IGNORED_SUFFIXES = frozenset((".pyc", ".pyo"))


class LearnerViewError(Exception):
    """The source tree cannot be exported without violating view policy."""


@dataclass(frozen=True, slots=True)
class ViewEntry:
    relative: Path
    is_directory: bool


def _is_ignored(path: Path) -> bool:
    return path.name in _IGNORED_NAMES or path.suffix in _IGNORED_SUFFIXES


def _validate_relative(relative: Path) -> None:
    blocked = []
    for part in relative.parts:
        normalized = part.casefold()
        stem = Path(normalized).stem
        if normalized in _FORBIDDEN_COMPONENTS or stem in {
            "answer",
            "answers",
            "solution",
            "solutions",
        }:
            blocked.append(part)
    if blocked:
        raise LearnerViewError(
            "learner-visible path contains forbidden component: " + str(relative)
        )


def _walk_entry(path: Path, relative: Path) -> list[ViewEntry]:
    _validate_relative(relative)
    if path.is_symlink():
        raise LearnerViewError("symbolic links are not exportable: " + str(relative))
    if path.is_file():
        return [ViewEntry(relative, False)]
    if not path.is_dir():
        raise LearnerViewError("special filesystem entry is not exportable: " + str(relative))

    entries = [ViewEntry(relative, True)]
    for child in sorted(path.iterdir(), key=lambda item: item.name):
        if _is_ignored(child):
            continue
        entries.extend(_walk_entry(child, relative / child.name))
    return entries


def plan_entries(source_root: Path) -> tuple[ViewEntry, ...]:
    """Return the exact sorted export plan after validating source entry types."""

    source_root = source_root.resolve(strict=True)
    if not source_root.is_dir():
        raise LearnerViewError("source root is not a directory")

    entries: list[ViewEntry] = []
    for name in LEARNER_TOP_LEVEL:
        source = source_root / name
        if not os.path.lexists(source):
            raise LearnerViewError("required learner entry is missing: " + name)
        expected_directory = name in _DIRECTORY_TOP_LEVEL
        if expected_directory != source.is_dir() or source.is_symlink():
            expected = "directory" if expected_directory else "regular file"
            raise LearnerViewError(name + " must be a " + expected)
        entries.extend(_walk_entry(source, Path(name)))
    return tuple(sorted(entries, key=lambda entry: str(entry.relative)))


def audit_view(view_root: Path) -> tuple[str, ...]:
    """Validate a materialized view and return its complete relative path list."""

    view_root = view_root.resolve(strict=True)
    if not view_root.is_dir():
        raise LearnerViewError("learner view is not a directory")
    observed_top = tuple(sorted(path.name for path in view_root.iterdir()))
    expected_top = tuple(sorted(LEARNER_TOP_LEVEL))
    if observed_top != expected_top:
        raise LearnerViewError("learner view top-level entries do not match the allowlist")

    observed: list[str] = []
    for path in sorted(view_root.rglob("*"), key=lambda item: str(item.relative_to(view_root))):
        relative = path.relative_to(view_root)
        if _is_ignored(path):
            raise LearnerViewError("transient artifact present in learner view: " + str(relative))
        _validate_relative(relative)
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise LearnerViewError("non-regular learner view entry: " + str(relative))
        observed.append(str(relative))
    return tuple(observed)


def materialize(source_root: Path, destination: Path) -> tuple[ViewEntry, ...]:
    """Atomically create a new allowlisted view without overwriting a destination."""

    source_root = source_root.resolve(strict=True)
    destination_parent = destination.parent.resolve(strict=True)
    destination = destination_parent / destination.name
    if os.path.lexists(destination):
        raise LearnerViewError("destination already exists: " + str(destination))

    try:
        internal = destination.relative_to(source_root)
    except ValueError:
        internal = None
    if internal is not None and internal.parts and internal.parts[0] in LEARNER_TOP_LEVEL:
        raise LearnerViewError("destination cannot be inside a learner-visible source root")

    entries = plan_entries(source_root)
    staging = Path(
        tempfile.mkdtemp(prefix=".learner-view-building-", dir=destination_parent)
    )
    try:
        staging.chmod(0o755)
        for entry in entries:
            source = source_root / entry.relative
            target = staging / entry.relative
            if entry.is_directory:
                target.mkdir(parents=True, exist_ok=True)
                target.chmod(0o755)
            else:
                if source.is_symlink() or not source.is_file():
                    raise LearnerViewError(
                        "source entry changed during export: " + str(entry.relative)
                    )
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                target.chmod(0o644)
        audit_view(staging)
        staging.replace(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return entries


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("destination", type=Path)
    options = parser.parse_args(argv)
    try:
        entries = materialize(options.source_root, options.destination)
    except (LearnerViewError, OSError) as error:
        print("error: " + str(error), file=sys.stderr)
        return 2
    file_count = sum(not entry.is_directory for entry in entries)
    print("learner_view_files={}".format(file_count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
