"""Lexical and filesystem checks for executable lookup within a rootfs."""

from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath

from .config import ContainerSpec
from .errors import RootfsError

_DEFAULT_PATH = "/bin:/usr/bin"


def _container_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not path.is_absolute():
        path = PurePosixPath("/") / path
    if ".." in path.parts:
        raise RootfsError("command paths must not contain '..'")
    return path


def _inspect_candidate(rootfs: Path, container_path: PurePosixPath) -> Path | None:
    candidate = rootfs.joinpath(*container_path.parts[1:])
    current = rootfs
    for part in container_path.parts[1:]:
        current = current / part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise RootfsError(f"cannot inspect command path: {exc.strerror or exc}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            raise RootfsError("command paths must not traverse symlinks")

    try:
        metadata = os.stat(candidate, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(metadata.st_mode):
        return None
    if metadata.st_mode & 0o111 == 0:
        return None
    return candidate


def resolve_executable(spec: ContainerSpec) -> Path:
    command = spec.argv[0]
    if "/" in command:
        container_candidates = [_container_path(command)]
    else:
        path_value = spec.env.get("PATH", _DEFAULT_PATH)
        if not path_value:
            raise RootfsError("PATH is empty and argv[0] contains no slash")
        container_candidates = []
        for entry in path_value.split(":"):
            if not entry:
                raise RootfsError("PATH must not contain empty entries")
            directory = PurePosixPath(entry)
            if not directory.is_absolute() or ".." in directory.parts:
                raise RootfsError("PATH entries must be absolute and traversal-free")
            container_candidates.append(directory / command)

    for container_candidate in container_candidates:
        resolved = _inspect_candidate(spec.rootfs, container_candidate)
        if resolved is not None:
            return resolved
    raise RootfsError(f"executable {command!r} was not found in the rootfs")
