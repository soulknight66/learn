"""Strict POSIX archive path validation."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from .errors import PathEscape


def safe_member_path(name: str) -> PurePosixPath:
    if not isinstance(name, str):
        raise PathEscape("archive member name must be a string")
    if not name or "\0" in name or "\\" in name:
        raise PathEscape("archive member name is empty or contains a forbidden character")
    if name.startswith("/"):
        raise PathEscape(f"absolute archive member path is forbidden: {name!r}")

    parts: list[str] = []
    for part in name.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise PathEscape(f"parent traversal is forbidden: {name!r}")
        parts.append(part)
    if not parts:
        raise PathEscape("archive member path must identify a non-root entry")

    result = PurePosixPath(*parts)
    if result.is_absolute() or any(part == ".." for part in result.parts):
        raise PathEscape(f"unsafe archive member path: {name!r}")
    return result


def resolve_beneath(root: Path, relative: PurePosixPath) -> Path:
    if not isinstance(relative, PurePosixPath):
        raise PathEscape("relative path must be a PurePosixPath")
    normalized = safe_member_path(relative.as_posix())
    resolved_root = Path(root).resolve(strict=False)
    current = resolved_root
    for part in normalized.parts:
        current = current / part
        if current.is_symlink():
            raise PathEscape(f"symbolic link in destination path: {current}")

    resolved_candidate = current.resolve(strict=False)
    if not resolved_candidate.is_relative_to(resolved_root):
        raise PathEscape(f"destination escapes assigned root: {relative}")
    return resolved_candidate
