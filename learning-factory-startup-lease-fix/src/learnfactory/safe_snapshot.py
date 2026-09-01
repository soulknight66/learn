from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path

from .isolation_limits import (
    CSDIY_EXAMINER_MAX_DEPTH,
    CSDIY_EXAMINER_MAX_ENTRIES,
    CSDIY_EXAMINER_MAX_FILES,
    CSDIY_EXAMINER_MAX_FILE_BYTES,
    CSDIY_EXAMINER_MAX_RAW_BYTES,
)
from .workspace import WorkspaceError


@dataclass(frozen=True)
class SnapshotLimits:
    """Hard resource bounds for one controller-owned filesystem snapshot."""

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
            raise ValueError("snapshot limits must be positive integers")


@dataclass
class _SnapshotUsage:
    entries: int = 0
    files: int = 0
    total_bytes: int = 0


# These are artifact-store safety bounds, not validation claims. A job whose
# dependency exceeds them remains unmaterialized and fails closed. CSDIY
# examiners use the much smaller textual-projection-compatible entry/depth cap.
GENERIC_ARTIFACT_SNAPSHOT_LIMITS = SnapshotLimits(
    max_entries=100_000,
    max_files=75_000,
    max_total_bytes=4 * 1024 * 1024 * 1024,
    max_file_bytes=1024 * 1024 * 1024,
    max_depth=128,
)

CSDIY_EXAMINER_SNAPSHOT_LIMITS = SnapshotLimits(
    max_entries=CSDIY_EXAMINER_MAX_ENTRIES,
    max_files=CSDIY_EXAMINER_MAX_FILES,
    max_total_bytes=CSDIY_EXAMINER_MAX_RAW_BYTES,
    max_file_bytes=CSDIY_EXAMINER_MAX_FILE_BYTES,
    max_depth=CSDIY_EXAMINER_MAX_DEPTH,
)


def _same_stat(left: os.stat_result, right: os.stat_result) -> bool:
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


def _open_source_directory(path: str | Path, *, dir_fd: int | None = None) -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise WorkspaceError("descriptor-safe dependency snapshots are unavailable")
    return os.open(
        path,
        os.O_RDONLY
        | os.O_CLOEXEC
        | os.O_NONBLOCK
        | os.O_NOFOLLOW
        | os.O_DIRECTORY,
        dir_fd=dir_fd,
    )


def _open_destination_directory(
    path: str | Path, *, dir_fd: int | None = None
) -> int:
    return os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_DIRECTORY,
        dir_fd=dir_fd,
    )


def _safe_name(name: str) -> None:
    if not name or name in {".", ".."} or "/" in name or "\x00" in name:
        raise WorkspaceError("dependency snapshot contains an unsafe entry name")
    try:
        name.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise WorkspaceError(
            "dependency snapshot contains a non-UTF-8 entry name"
        ) from error


def _discover_names(
    descriptor: int,
    usage: _SnapshotUsage,
    limits: SnapshotLimits,
) -> list[str]:
    """Stream names and stop before retaining the first over-limit entry."""

    names: list[str] = []
    with os.scandir(descriptor) as entries:
        for entry in entries:
            usage.entries += 1
            if usage.entries > limits.max_entries:
                raise WorkspaceError("dependency snapshot exceeds maximum entries")
            _safe_name(entry.name)
            names.append(entry.name)
    names.sort()
    return names


def _revalidate_namespace(descriptor: int, expected: list[str]) -> None:
    names: list[str] = []
    with os.scandir(descriptor) as entries:
        for entry in entries:
            # Never retain more names during revalidation than were admitted by
            # the bounded discovery pass.
            if len(names) >= len(expected):
                raise WorkspaceError("dependency snapshot directory entries changed")
            _safe_name(entry.name)
            names.append(entry.name)
    names.sort()
    if names != expected:
        raise WorkspaceError("dependency snapshot directory entries changed")


def _copy_regular_file(
    source_directory: int,
    destination_directory: int,
    name: str,
    before: os.stat_result,
) -> int:
    """Copy one already-budgeted file through pinned directory descriptors."""

    source_flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK | os.O_NOFOLLOW
    source = os.open(name, source_flags, dir_fd=source_directory)
    target: int | None = None
    target_created = False
    copied = 0
    try:
        opened = os.fstat(source)
        if not stat.S_ISREG(opened.st_mode) or not _same_stat(before, opened):
            raise WorkspaceError("dependency snapshot file changed before copy")
        target_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            target_flags |= os.O_NOFOLLOW
        target = os.open(
            name,
            target_flags,
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
                raise WorkspaceError("dependency snapshot file grew during copy")
            view = memoryview(chunk)
            while view:
                written = os.write(target, view)
                if written <= 0:
                    raise OSError("short dependency snapshot write")
                view = view[written:]
        after = os.fstat(source)
        if copied != before.st_size or not _same_stat(before, after):
            raise WorkspaceError("dependency snapshot file changed during copy")
        os.fchmod(target, before.st_mode & 0o777)
        target_info = os.fstat(target)
        if (
            not stat.S_ISREG(target_info.st_mode)
            or target_info.st_nlink != 1
            or target_info.st_size != copied
            or stat.S_IMODE(target_info.st_mode) != (before.st_mode & 0o777)
        ):
            raise WorkspaceError("dependency snapshot target file is unsafe")
        return copied
    except BaseException:
        if target_created:
            try:
                os.unlink(name, dir_fd=destination_directory)
            except OSError:
                pass
        raise
    finally:
        if target is not None:
            os.close(target)
        os.close(source)


def _copy_directory(
    source: int,
    destination: int,
    relative_parts: tuple[str, ...],
    usage: _SnapshotUsage,
    limits: SnapshotLimits,
    seen_directories: set[tuple[int, int]],
) -> None:
    directory_before = os.fstat(source)
    if not stat.S_ISDIR(directory_before.st_mode):
        raise WorkspaceError("dependency snapshot directory changed type")
    identity = (int(directory_before.st_dev), int(directory_before.st_ino))
    if identity in seen_directories:
        raise WorkspaceError("dependency snapshot directory aliases a prior inode")
    seen_directories.add(identity)
    names = _discover_names(source, usage, limits)
    for name in names:
        child_parts = (*relative_parts, name)
        if len(child_parts) > limits.max_depth:
            raise WorkspaceError("dependency snapshot exceeds maximum depth")
        before = os.stat(name, dir_fd=source, follow_symlinks=False)
        if stat.S_ISDIR(before.st_mode):
            child_source = _open_source_directory(name, dir_fd=source)
            try:
                opened = os.fstat(child_source)
                if not _same_stat(before, opened):
                    raise WorkspaceError(
                        "dependency snapshot directory changed before copy"
                    )
                os.mkdir(name, mode=0o700, dir_fd=destination)
                child_destination = _open_destination_directory(
                    name, dir_fd=destination
                )
                try:
                    _copy_directory(
                        child_source,
                        child_destination,
                        child_parts,
                        usage,
                        limits,
                        seen_directories,
                    )
                    os.fchmod(child_destination, before.st_mode & 0o777)
                finally:
                    os.close(child_destination)
            finally:
                os.close(child_source)
        elif stat.S_ISREG(before.st_mode):
            if before.st_nlink != 1:
                raise WorkspaceError(
                    "dependency snapshot file has an external hard-link alias"
                )
            usage.files += 1
            if usage.files > limits.max_files:
                raise WorkspaceError("dependency snapshot exceeds maximum files")
            if before.st_size > limits.max_file_bytes:
                raise WorkspaceError("dependency snapshot file exceeds maximum bytes")
            if usage.total_bytes + before.st_size > limits.max_total_bytes:
                raise WorkspaceError("dependency snapshot exceeds maximum total bytes")
            copied = _copy_regular_file(source, destination, name, before)
            usage.total_bytes += copied
        elif stat.S_ISLNK(before.st_mode):
            target = os.readlink(name, dir_fd=source)
            after_link = os.stat(name, dir_fd=source, follow_symlinks=False)
            if not _same_stat(before, after_link):
                raise WorkspaceError("dependency snapshot symlink changed during copy")
            os.symlink(target, name, dir_fd=destination)
        else:
            raise WorkspaceError("dependency snapshot contains a special file")
        named_after = os.stat(name, dir_fd=source, follow_symlinks=False)
        if not _same_stat(before, named_after):
            raise WorkspaceError("dependency snapshot named entry changed during copy")
    _revalidate_namespace(source, names)
    if not _same_stat(directory_before, os.fstat(source)):
        raise WorkspaceError("dependency snapshot directory changed during copy")


def _discard_partial_snapshot(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def snapshot_tree(
    source: Path,
    destination: Path,
    *,
    limits: SnapshotLimits = GENERIC_ARTIFACT_SNAPSHOT_LIMITS,
) -> Path:
    """Take a bounded, no-follow, race-detecting dependency tree snapshot."""

    source_named_before = source.lstat()
    if not stat.S_ISDIR(source_named_before.st_mode):
        raise WorkspaceError("dependency snapshot source must be a directory")
    if destination.exists() or destination.is_symlink():
        raise WorkspaceError("dependency snapshot destination already exists")
    try:
        source_descriptor = _open_source_directory(source)
    except OSError as error:
        raise WorkspaceError("cannot pin dependency snapshot root") from error
    try:
        source_opened = os.fstat(source_descriptor)
        if not _same_stat(source_named_before, source_opened):
            raise WorkspaceError("dependency snapshot root changed before copy")
        destination.mkdir(mode=0o700)
        destination_descriptor = _open_destination_directory(destination)
        try:
            _copy_directory(
                source_descriptor,
                destination_descriptor,
                (),
                _SnapshotUsage(),
                limits,
                set(),
            )
            os.fchmod(
                destination_descriptor, source_named_before.st_mode & 0o777
            )
        finally:
            os.close(destination_descriptor)
        source_named_after = source.lstat()
        if not _same_stat(source_named_before, source_named_after):
            raise WorkspaceError("dependency snapshot root name changed during copy")
        return destination
    except BaseException as error:
        try:
            _discard_partial_snapshot(destination)
        except OSError as cleanup_error:
            error.add_note(
                f"partial dependency snapshot cleanup also failed: {cleanup_error}"
            )
        raise
    finally:
        os.close(source_descriptor)
