from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .isolation_limits import (
    CSDIY_EXAMINER_MAX_DEPTH,
    CSDIY_EXAMINER_MAX_ENTRIES,
    CSDIY_EXAMINER_MAX_FILES,
    CSDIY_EXAMINER_MAX_FILE_BYTES,
    CSDIY_EXAMINER_MAX_RAW_BYTES,
)
from .util import canonical_json, tree_sha256
from .workspace import WorkspaceError, safe_relative


SUBMISSION_BINDING_SCHEMA_VERSION = 1
SUBMISSION_BINDING_VALIDATOR = "csdiy-student-submission-binding"
SUBMISSION_INPUT_INTEGRITY_VALIDATOR = "declared-inputs-remained-immutable"
SUBMISSION_DESTINATION = "STUDENT_SUBMISSION"
SUBMISSION_VISIBILITY = "complete-filtered-student-artifact-tree"
SUBMISSION_SEPARATION_POLICY = "csdiy-examiner-submission-v1"

# These names are never learner evidence. Some are examiner-only material and
# some are mutable caches/control-plane state. A sensitive name is rejected;
# disposable state is omitted and recorded in the projection evidence.
_FORBIDDEN_NAMES = frozenset(
    {
        "examiner_only",
        "hidden",
        "hidden-tests",
        "hidden_tests",
        "novel_check.md",
        "reference",
        "references",
        "rubric.md",
        "sealed",
    }
)
_DISPOSABLE_DIRECTORY_NAMES = frozenset(
    {
        ".agents",
        ".codex",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
        "venv",
    }
)
_DISPOSABLE_ROOT_FILES = frozenset(
    {
        ".factory-workspace",
        "course_brief.md",
        "comprehension.md",
        "job.md",
        "study_task.md",
    }
)
_DISPOSABLE_SUFFIXES = frozenset(
    {".class", ".o", ".obj", ".pyc", ".pyo", ".so"}
)
_SOURCE_SUFFIXES = frozenset(
    {
        ".c", ".cc", ".cpp", ".cs", ".cxx", ".go", ".h", ".hh",
        ".hpp", ".java", ".js", ".kt", ".lua", ".ml", ".py",
        ".rb", ".rs", ".scala", ".sh", ".sql", ".swift", ".ts",
        ".tsx", ".zig",
    }
)
_MAX_ENTRIES = 20_000
_MAX_FILES = 10_000
_MAX_TOTAL_BYTES = 256 * 1024 * 1024
_MAX_FILE_BYTES = 32 * 1024 * 1024
_MAX_DEPTH = 80


@dataclass(frozen=True)
class StudentSubmissionLimits:
    max_entries: int
    max_files: int
    max_total_bytes: int
    max_file_bytes: int
    max_depth: int

    def __post_init__(self) -> None:
        values = (
            self.max_entries,
            self.max_files,
            self.max_total_bytes,
            self.max_file_bytes,
            self.max_depth,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in values
        ):
            raise ValueError("student submission limits must be positive integers")


DEFAULT_SUBMISSION_LIMITS = StudentSubmissionLimits(
    _MAX_ENTRIES,
    _MAX_FILES,
    _MAX_TOTAL_BYTES,
    _MAX_FILE_BYTES,
    _MAX_DEPTH,
)

# Match the static examiner transport. Passing this at the student-to-examiner
# seam ensures no tree larger than the eventual textual projection is first
# materialized in a temporary directory.
EXAMINER_SUBMISSION_LIMITS = StudentSubmissionLimits(
    max_entries=CSDIY_EXAMINER_MAX_ENTRIES,
    max_files=CSDIY_EXAMINER_MAX_FILES,
    max_total_bytes=CSDIY_EXAMINER_MAX_RAW_BYTES,
    max_file_bytes=CSDIY_EXAMINER_MAX_FILE_BYTES,
    max_depth=CSDIY_EXAMINER_MAX_DEPTH,
)


@dataclass
class _SubmissionUsage:
    entries: int = 0
    files: int = 0
    total_bytes: int = 0


@dataclass
class _SubmissionEntry:
    name: str
    relative: str
    fingerprint: os.stat_result
    selected_file: bool = False
    child: _SubmissionDirectory | None = None


@dataclass
class _SubmissionDirectory:
    fingerprint: os.stat_result
    names: list[str]
    entries: list[_SubmissionEntry]
    selected_file_count: int


def _same_submission_stat(left: os.stat_result, right: os.stat_result) -> bool:
    return all(
        getattr(left, name) == getattr(right, name)
        for name in (
            "st_dev",
            "st_ino",
            "st_mode",
            "st_nlink",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
        )
    )


def _open_submission_directory(
    path: str | Path, *, dir_fd: int | None = None
) -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise WorkspaceError("descriptor-safe student projection is unavailable")
    return os.open(
        path,
        os.O_RDONLY
        | os.O_CLOEXEC
        | os.O_NONBLOCK
        | os.O_NOFOLLOW
        | os.O_DIRECTORY,
        dir_fd=dir_fd,
    )


def _submission_name(name: str) -> None:
    if not name or name in {".", ".."} or "/" in name or "\x00" in name:
        raise WorkspaceError("student submission contains an unsafe entry name")
    try:
        name.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise WorkspaceError(
            "student submission contains a non-UTF-8 entry name"
        ) from error


def _bounded_local_names(descriptor: int, maximum: int) -> list[str]:
    names: list[str] = []
    with os.scandir(descriptor) as entries:
        for entry in entries:
            if len(names) >= maximum:
                raise WorkspaceError("student artifact root exceeds maximum entries")
            _submission_name(entry.name)
            names.append(entry.name)
    names.sort()
    return names


def _revalidate_submission_namespace(
    descriptor: int, expected: list[str]
) -> None:
    names: list[str] = []
    with os.scandir(descriptor) as entries:
        for entry in entries:
            if len(names) >= len(expected):
                raise WorkspaceError("student submission directory entries changed")
            _submission_name(entry.name)
            names.append(entry.name)
    names.sort()
    if names != expected:
        raise WorkspaceError("student submission directory entries changed")


def _plan_submission_directory(
    descriptor: int,
    relative_parts: tuple[str, ...],
    limits: StudentSubmissionLimits,
    usage: _SubmissionUsage,
    seen_directories: set[tuple[int, int]],
    excluded: list[str],
    sensitive: list[str],
    student_named_roots: list[str],
) -> _SubmissionDirectory:
    before = os.fstat(descriptor)
    if not stat.S_ISDIR(before.st_mode):
        raise WorkspaceError("student submission directory changed type")
    identity = (int(before.st_dev), int(before.st_ino))
    if identity in seen_directories:
        raise WorkspaceError("student submission directory aliases a prior inode")
    seen_directories.add(identity)
    names: list[str] = []
    with os.scandir(descriptor) as discovered:
        for item in discovered:
            usage.entries += 1
            # Fail before retaining or inspecting the 4,097th examiner entry.
            if usage.entries > limits.max_entries:
                raise WorkspaceError("student submission exceeds maximum entries")
            _submission_name(item.name)
            names.append(item.name)
    names.sort()
    planned: list[_SubmissionEntry] = []
    selected_file_count = 0
    for name in names:
        child_parts = (*relative_parts, name)
        if len(child_parts) > limits.max_depth:
            raise WorkspaceError("student submission exceeds maximum tree depth")
        relative = "/".join(child_parts)
        lowered = name.casefold()
        named_before = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        entry = _SubmissionEntry(name, relative, named_before)
        if stat.S_ISLNK(named_before.st_mode):
            raise WorkspaceError(f"student submission contains a symlink: {relative}")
        if stat.S_ISDIR(named_before.st_mode):
            if _forbidden_file_name(name):
                sensitive.append(relative)
            elif lowered in _DISPOSABLE_DIRECTORY_NAMES:
                excluded.append(relative + "/")
            elif not relative_parts and re.fullmatch(r"student[-_].+", lowered):
                student_named_roots.append(relative)
            else:
                child = _open_submission_directory(name, dir_fd=descriptor)
                try:
                    opened = os.fstat(child)
                    if not _same_submission_stat(named_before, opened):
                        raise WorkspaceError(
                            f"student submission entry changed before traversal: {relative}"
                        )
                    entry.child = _plan_submission_directory(
                        child,
                        child_parts,
                        limits,
                        usage,
                        seen_directories,
                        excluded,
                        sensitive,
                        student_named_roots,
                    )
                    selected_file_count += entry.child.selected_file_count
                finally:
                    os.close(child)
        elif stat.S_ISREG(named_before.st_mode):
            if named_before.st_nlink != 1:
                raise WorkspaceError(
                    f"student submission file has an external hard-link alias: {relative}"
                )
            if _forbidden_file_name(name):
                sensitive.append(relative)
            elif (not relative_parts and lowered in _DISPOSABLE_ROOT_FILES) or (
                Path(name).suffix.casefold() in _DISPOSABLE_SUFFIXES
            ):
                excluded.append(relative)
            else:
                usage.files += 1
                if usage.files > limits.max_files:
                    raise WorkspaceError("student submission exceeds maximum files")
                if named_before.st_size > limits.max_file_bytes:
                    raise WorkspaceError(
                        f"student submission file is too large: {relative}"
                    )
                if usage.total_bytes + named_before.st_size > limits.max_total_bytes:
                    raise WorkspaceError(
                        "student submission exceeds maximum total bytes"
                    )
                usage.total_bytes += int(named_before.st_size)
                entry.selected_file = True
                selected_file_count += 1
        else:
            raise WorkspaceError(
                f"student submission contains a special file: {relative}"
            )
        named_after = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        if not _same_submission_stat(named_before, named_after):
            raise WorkspaceError(
                f"student submission named entry changed during planning: {relative}"
            )
        planned.append(entry)
    _revalidate_submission_namespace(descriptor, names)
    if not _same_submission_stat(before, os.fstat(descriptor)):
        raise WorkspaceError("student submission directory changed during planning")
    return _SubmissionDirectory(before, names, planned, selected_file_count)


def _copy_submission_file(
    source_directory: int,
    destination_directory: int,
    entry: _SubmissionEntry,
) -> dict[str, Any]:
    before = entry.fingerprint
    source = os.open(
        entry.name,
        os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK | os.O_NOFOLLOW,
        dir_fd=source_directory,
    )
    target: int | None = None
    target_created = False
    digest = hashlib.sha256()
    copied = 0
    try:
        opened = os.fstat(source)
        if not stat.S_ISREG(opened.st_mode) or not _same_submission_stat(before, opened):
            raise WorkspaceError(
                f"student submission file changed before copy: {entry.relative}"
            )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
        target = os.open(
            entry.name,
            flags,
            0o600,
            dir_fd=destination_directory,
        )
        target_created = True
        remaining = int(before.st_size) + 1
        while remaining:
            chunk = os.read(source, min(128 * 1024, remaining))
            if not chunk:
                break
            copied += len(chunk)
            remaining -= len(chunk)
            if copied > before.st_size:
                raise WorkspaceError(
                    f"student submission file grew during copy: {entry.relative}"
                )
            digest.update(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(target, view)
                if written <= 0:
                    raise OSError("short student submission write")
                view = view[written:]
        if copied != before.st_size or not _same_submission_stat(
            before, os.fstat(source)
        ):
            raise WorkspaceError(
                f"student submission file changed during copy: {entry.relative}"
            )
        # Preserve ordinary rwx bits only.  Never copy setuid, setgid, sticky,
        # ACL-like or implementation-specific mode bits across this trust seam.
        expected_mode = (before.st_mode & 0o777) & ~0o222
        os.fchmod(target, expected_mode)
        target_info = os.fstat(target)
        if (
            not stat.S_ISREG(target_info.st_mode)
            or target_info.st_nlink != 1
            or target_info.st_size != copied
            or stat.S_IMODE(target_info.st_mode) != expected_mode
        ):
            raise WorkspaceError(
                f"student submission copy is unsafe: {entry.relative}"
            )
        return {
            "path": entry.relative,
            "size_bytes": copied,
            "sha256": digest.hexdigest(),
        }
    except BaseException:
        if target_created:
            try:
                os.unlink(entry.name, dir_fd=destination_directory)
            except OSError:
                pass
        raise
    finally:
        if target is not None:
            os.close(target)
        os.close(source)


def _copy_planned_submission(
    source: int,
    destination: int,
    plan: _SubmissionDirectory,
    selected: list[dict[str, Any]],
) -> None:
    if not _same_submission_stat(plan.fingerprint, os.fstat(source)):
        raise WorkspaceError("student submission directory changed before copy")
    _revalidate_submission_namespace(source, plan.names)
    for entry in plan.entries:
        named_before = os.stat(entry.name, dir_fd=source, follow_symlinks=False)
        if not _same_submission_stat(entry.fingerprint, named_before):
            raise WorkspaceError(
                f"student submission entry changed before copy: {entry.relative}"
            )
        if entry.selected_file:
            selected.append(
                _copy_submission_file(source, destination, entry)
            )
        elif entry.child is not None and entry.child.selected_file_count:
            child_source = _open_submission_directory(entry.name, dir_fd=source)
            try:
                if not _same_submission_stat(
                    entry.fingerprint, os.fstat(child_source)
                ):
                    raise WorkspaceError(
                        f"student submission directory changed before copy: {entry.relative}"
                    )
                os.mkdir(entry.name, mode=0o700, dir_fd=destination)
                child_destination = os.open(
                    entry.name,
                    os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_DIRECTORY,
                    dir_fd=destination,
                )
                try:
                    _copy_planned_submission(
                        child_source, child_destination, entry.child, selected
                    )
                finally:
                    os.close(child_destination)
            finally:
                os.close(child_source)
        named_after = os.stat(entry.name, dir_fd=source, follow_symlinks=False)
        if not _same_submission_stat(entry.fingerprint, named_after):
            raise WorkspaceError(
                f"student submission named entry changed during copy: {entry.relative}"
            )
    _revalidate_submission_namespace(source, plan.names)
    if not _same_submission_stat(plan.fingerprint, os.fstat(source)):
        raise WorkspaceError("student submission directory changed during copy")


def _discard_student_projection(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _is_sha256(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _forbidden_file_name(name: str) -> bool:
    lowered = name.casefold()
    stem = Path(lowered).stem
    return bool(
        lowered in _FORBIDDEN_NAMES
        or stem in {
            "hidden-test",
            "hidden-tests",
            "hidden_test",
            "hidden_tests",
            "novel_check",
            "rubric",
        }
    )


@dataclass(frozen=True)
class StudentSubmissionBinding:
    student_job_id: str
    student_artifact_type: str
    destination: str


def parse_student_submission_binding(raw: object) -> StudentSubmissionBinding:
    """Parse the control-plane-owned examiner input contract exactly."""

    if not isinstance(raw, dict) or set(raw) != {
        "schema_version",
        "student_job_id",
        "student_artifact_type",
        "destination",
        "visibility",
        "separation_policy",
    }:
        raise ValueError("student_submission_binding has an invalid shape")
    if raw["schema_version"] != SUBMISSION_BINDING_SCHEMA_VERSION:
        raise ValueError("unsupported student_submission_binding schema version")
    if raw["visibility"] != SUBMISSION_VISIBILITY:
        raise ValueError("unsupported student submission visibility policy")
    if raw["separation_policy"] != SUBMISSION_SEPARATION_POLICY:
        raise ValueError("unsupported student submission separation policy")
    values: dict[str, str] = {}
    for name in ("student_job_id", "student_artifact_type", "destination"):
        value = raw[name]
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError(f"student_submission_binding {name} is invalid")
        values[name] = value
    if values["destination"] != SUBMISSION_DESTINATION:
        raise ValueError("student submission must use the protected canonical destination")
    safe_relative(values["destination"])
    return StudentSubmissionBinding(
        values["student_job_id"],
        values["student_artifact_type"],
        values["destination"],
    )


def student_submission_binding_payload(
    student_job_id: str, student_artifact_type: str
) -> dict[str, Any]:
    return {
        "schema_version": SUBMISSION_BINDING_SCHEMA_VERSION,
        "student_job_id": student_job_id,
        "student_artifact_type": student_artifact_type,
        "destination": SUBMISSION_DESTINATION,
        "visibility": SUBMISSION_VISIBILITY,
        "separation_policy": SUBMISSION_SEPARATION_POLICY,
    }


def project_student_submission(
    source: Path,
    destination: Path,
    *,
    limits: StudentSubmissionLimits = DEFAULT_SUBMISSION_LIMITS,
) -> dict[str, Any]:
    """Create the exact examiner-visible student tree and its manifest evidence.

    The caller has already verified the immutable artifact's tree checksum. This
    projection removes known staged course inputs and disposable build state,
    rejects examiner/reference material, and preserves every remaining regular
    learner file. It never follows links.
    """

    source_named_before = source.lstat()
    if not stat.S_ISDIR(source_named_before.st_mode):
        raise WorkspaceError("student artifact root is missing or unsafe")
    if destination.exists() or destination.is_symlink():
        raise WorkspaceError("student submission projection destination exists")
    source_descriptor = _open_submission_directory(source)
    projection_descriptor: int | None = None
    canonical_fingerprint: os.stat_result | None = None
    source_namespace: list[str] | None = None
    source_entry_fingerprints: dict[str, os.stat_result] = {}
    destination_descriptor: int | None = None
    try:
        source_opened = os.fstat(source_descriptor)
        if not _same_submission_stat(source_named_before, source_opened):
            raise WorkspaceError("student artifact root changed before projection")
        try:
            canonical_fingerprint = os.stat(
                "student_work", dir_fd=source_descriptor, follow_symlinks=False
            )
        except FileNotFoundError:
            canonical_fingerprint = None

        if canonical_fingerprint is not None:
            if not stat.S_ISDIR(canonical_fingerprint.st_mode):
                raise WorkspaceError("student_work is not a safe directory")
            source_namespace = _bounded_local_names(
                source_descriptor, limits.max_entries
            )
            for name in source_namespace:
                fingerprint = os.stat(
                    name, dir_fd=source_descriptor, follow_symlinks=False
                )
                source_entry_fingerprints[name] = fingerprint
                if name == "student_work":
                    continue
                lowered = name.casefold()
                if stat.S_ISLNK(fingerprint.st_mode) or not (
                    stat.S_ISREG(fingerprint.st_mode)
                    or stat.S_ISDIR(fingerprint.st_mode)
                ):
                    raise WorkspaceError(
                        f"student artifact contains a link or special root: {name}"
                    )
                if lowered in _FORBIDDEN_NAMES or (
                    stat.S_ISREG(fingerprint.st_mode)
                    and _forbidden_file_name(name)
                ):
                    raise WorkspaceError(
                        f"student artifact contains examiner/reference material: {name}"
                    )
                if not (
                    lowered in _DISPOSABLE_DIRECTORY_NAMES
                    or lowered in _DISPOSABLE_ROOT_FILES
                ):
                    raise WorkspaceError(
                        "student artifact has learner output outside canonical student_work: "
                        + name
                    )
            projection_descriptor = _open_submission_directory(
                "student_work", dir_fd=source_descriptor
            )
            if not _same_submission_stat(
                canonical_fingerprint, os.fstat(projection_descriptor)
            ):
                raise WorkspaceError("student_work changed before projection")
            source_prefix = "student_work"
        else:
            projection_descriptor = os.dup(source_descriptor)
            source_prefix = "."

        usage = _SubmissionUsage()
        excluded: list[str] = []
        sensitive: list[str] = []
        student_named_roots: list[str] = []
        plan = _plan_submission_directory(
            projection_descriptor,
            (),
            limits,
            usage,
            set(),
            excluded,
            sensitive,
            student_named_roots,
        )
        if sensitive:
            raise WorkspaceError(
                "student artifact contains examiner/reference material: "
                + ", ".join(sorted(sensitive)[:20])
            )
        if student_named_roots:
            raise WorkspaceError(
                "student artifact contains another student-shaped root: "
                + ", ".join(sorted(student_named_roots)[:20])
            )
        if plan.selected_file_count == 0:
            raise WorkspaceError(
                "student submission projection contains no learner files"
            )

        # No destination is allocated until the complete tree passes every
        # entry/file/byte/depth and separation check above.
        destination.mkdir(mode=0o700)
        destination_descriptor = os.open(
            destination,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_DIRECTORY,
        )
        selected: list[dict[str, Any]] = []
        _copy_planned_submission(
            projection_descriptor, destination_descriptor, plan, selected
        )
        os.close(destination_descriptor)
        destination_descriptor = None
        if len(selected) != plan.selected_file_count:
            raise WorkspaceError("student submission copy count is inconsistent")

        if source_namespace is not None:
            _revalidate_submission_namespace(source_descriptor, source_namespace)
            for name, fingerprint in source_entry_fingerprints.items():
                if not _same_submission_stat(
                    fingerprint,
                    os.stat(name, dir_fd=source_descriptor, follow_symlinks=False),
                ):
                    raise WorkspaceError(
                        "student artifact root entry changed during projection"
                    )
        if not _same_submission_stat(source_opened, os.fstat(source_descriptor)):
            raise WorkspaceError("student artifact root changed during projection")
        source_named_after = source.lstat()
        if not _same_submission_stat(source_named_before, source_named_after):
            raise WorkspaceError("student artifact root name changed during projection")

        selected.sort(key=lambda item: item["path"])
        excluded.sort()
        paths_manifest = [
            {
                "path": item["path"],
                "size_bytes": item["size_bytes"],
                "sha256": item["sha256"],
            }
            for item in selected
        ]
        code_paths = [
            item["path"]
            for item in selected
            if Path(item["path"]).suffix.casefold() in _SOURCE_SUFFIXES
        ]
        test_paths = [
            item["path"]
            for item in selected
            if any("test" in part.casefold() for part in Path(item["path"]).parts)
        ]
        return {
            "schema_version": 1,
            "source_prefix": source_prefix,
            "regular_file_count": len(selected),
            "total_bytes": usage.total_bytes,
            "code_file_count": len(code_paths),
            "test_file_count": len(test_paths),
            "code_path_samples": sorted(code_paths)[:20],
            "test_path_samples": sorted(test_paths)[:20],
            "excluded_paths": excluded[:100],
            "excluded_path_count": len(excluded),
            "paths_manifest_sha256": hashlib.sha256(
                canonical_json(paths_manifest).encode("utf-8")
            ).hexdigest(),
            "projected_checksum_algorithm": "tree-sha256-v2",
            "projected_checksum": tree_sha256(destination),
            "limits": {
                "max_entries": limits.max_entries,
                "max_files": limits.max_files,
                "max_total_bytes": limits.max_total_bytes,
                "max_file_bytes": limits.max_file_bytes,
                "max_depth": limits.max_depth,
            },
        }
    except BaseException as error:
        if destination_descriptor is not None:
            os.close(destination_descriptor)
        try:
            _discard_student_projection(destination)
        except OSError as cleanup_error:
            error.add_note(
                f"partial student projection cleanup also failed: {cleanup_error}"
            )
        raise
    finally:
        if projection_descriptor is not None:
            os.close(projection_descriptor)
        os.close(source_descriptor)


def submission_binding_evidence(
    raw_contract: object, staged_inputs: list[dict[str, Any]]
) -> dict[str, Any]:
    """Resolve one staged projection into evidence safe for progression."""

    contract = parse_student_submission_binding(raw_contract)
    matches = [
        item
        for item in staged_inputs
        if item.get("path") == contract.destination
        and item.get("origin") == "dependency-artifact"
        and item.get("job_id") == contract.student_job_id
        and item.get("artifact_type") == contract.student_artifact_type
        and item.get("artifact_subpath") == "."
    ]
    if len(matches) != 1:
        raise ValueError("student submission binding did not resolve to exactly one staged tree")
    item = matches[0]
    projection = item.get("student_submission_projection")
    required_text = (
        "artifact_id",
        "artifact_checksum",
        "artifact_checksum_algorithm",
        "checksum",
        "checksum_algorithm",
    )
    if (
        item.get("kind") != "directory"
        or item.get("artifact_checksum_algorithm") != "tree-sha256-v2"
        or item.get("checksum_algorithm") != "tree-sha256-v2"
        or not isinstance(item.get("artifact_attempt"), int)
        or isinstance(item.get("artifact_attempt"), bool)
        or not isinstance(projection, dict)
        or any(not isinstance(item.get(name), str) for name in required_text)
    ):
        raise ValueError("student submission staged evidence is malformed")
    if projection.get("projected_checksum_algorithm") != "tree-sha256-v2":
        raise ValueError("student submission projection checksum algorithm is invalid")
    if (
        not _is_sha256(item.get("checksum"))
        or not _is_sha256(projection.get("projected_checksum"))
        or projection.get("projected_checksum") != item.get("checksum")
        or not _is_sha256(projection.get("paths_manifest_sha256"))
    ):
        raise ValueError("student submission projection evidence is inconsistent")
    body = {
        "schema_version": SUBMISSION_BINDING_SCHEMA_VERSION,
        "separation_policy": SUBMISSION_SEPARATION_POLICY,
        "visibility": SUBMISSION_VISIBILITY,
        "student_job_id": contract.student_job_id,
        "artifact_id": item["artifact_id"],
        "artifact_type": item["artifact_type"],
        "artifact_attempt": item["artifact_attempt"],
        "artifact_checksum_algorithm": item["artifact_checksum_algorithm"],
        "artifact_checksum": item["artifact_checksum"],
        "staged_path": contract.destination,
        "staged_checksum_algorithm": item["checksum_algorithm"],
        "staged_checksum": item["checksum"],
        "projection": projection,
        "input_integrity_validator": SUBMISSION_INPUT_INTEGRITY_VALIDATOR,
    }
    return {
        **body,
        "binding_sha256": hashlib.sha256(
            canonical_json(body).encode("utf-8")
        ).hexdigest(),
    }
