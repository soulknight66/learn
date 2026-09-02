"""Validated, quota-bounded tar layer application."""

from __future__ import annotations

import os
import shutil
import stat
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .errors import InvalidLayer, PathEscape
from .paths import resolve_beneath, safe_member_path


@dataclass(frozen=True)
class LayerLimits:
    max_members: int = 1024
    max_file_bytes: int = 8 * 1024 * 1024
    max_total_bytes: int = 32 * 1024 * 1024

    def __post_init__(self) -> None:
        if self.max_members < 1 or self.max_file_bytes < 0 or self.max_total_bytes < 0:
            raise ValueError("layer limits must be non-negative and allow at least one member")


@dataclass(frozen=True)
class _Entry:
    member: tarfile.TarInfo
    path: PurePosixPath
    whiteout: str | None


class LayerApplier:
    _COPY_CHUNK = 128 * 1024

    def __init__(self, limits: LayerLimits | None = None) -> None:
        self.limits = limits or LayerLimits()

    def _read_and_preflight(self, archive: tarfile.TarFile) -> list[_Entry]:
        entries: list[_Entry] = []
        seen: set[PurePosixPath] = set()
        total_bytes = 0

        while True:
            try:
                member = archive.next()
            except (tarfile.TarError, OSError, EOFError) as exc:
                raise InvalidLayer(f"cannot parse layer header: {exc}") from exc
            if member is None:
                break
            if len(entries) >= self.limits.max_members:
                raise InvalidLayer("layer member count exceeds configured limit")

            path = safe_member_path(member.name)
            if path in seen:
                raise InvalidLayer(f"duplicate normalized member path: {path}")
            seen.add(path)

            if member.isdir():
                if member.size != 0:
                    raise InvalidLayer(f"directory has nonzero payload: {path}")
            elif member.isfile():
                if getattr(member, "sparse", None):
                    raise InvalidLayer(f"sparse files are not supported: {path}")
                if member.size < 0 or member.size > self.limits.max_file_bytes:
                    raise InvalidLayer(f"file exceeds configured limit: {path}")
                total_bytes += member.size
                if total_bytes > self.limits.max_total_bytes:
                    raise InvalidLayer("layer payload exceeds configured total limit")
            else:
                raise InvalidLayer(f"unsupported tar member type for {path}")

            whiteout: str | None = None
            basename = path.name
            if basename.startswith(".wh."):
                if not member.isfile() or member.size != 0:
                    raise InvalidLayer(f"whiteout must be an empty regular file: {path}")
                if basename == ".wh..wh..opq":
                    whiteout = "opaque"
                elif basename == ".wh.":
                    raise InvalidLayer(f"whiteout has an empty target: {path}")
                else:
                    whiteout = "remove"
            entries.append(_Entry(member, path, whiteout))

        ordinary = [entry for entry in entries if entry.whiteout is None]
        ordinary_files = {entry.path for entry in ordinary if entry.member.isfile()}
        for entry in ordinary:
            for parent in entry.path.parents:
                if parent == PurePosixPath("."):
                    break
                if parent in ordinary_files:
                    raise InvalidLayer(f"regular file is also an ancestor in the layer: {parent}")
        return entries

    @staticmethod
    def _assert_regular_tree(root: Path) -> None:
        if not root.exists():
            return
        if root.is_symlink() or not root.is_dir():
            raise InvalidLayer("layer destination must be a real directory")
        pending = [root]
        while pending:
            directory = pending.pop()
            try:
                children = list(os.scandir(directory))
            except OSError as exc:
                raise InvalidLayer(f"cannot inspect destination: {exc}") from exc
            for child in children:
                if child.is_symlink():
                    raise InvalidLayer(f"destination contains a symbolic link: {child.path}")
                if child.is_dir(follow_symlinks=False):
                    pending.append(Path(child.path))
                elif not child.is_file(follow_symlinks=False):
                    raise InvalidLayer(f"destination contains a special file: {child.path}")

    @staticmethod
    def _remove(path: Path) -> None:
        if path.is_symlink():
            raise InvalidLayer(f"refusing to remove symbolic link in rootfs: {path}")
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            if not path.is_file():
                raise InvalidLayer(f"refusing to remove special file: {path}")
            path.unlink()

    @staticmethod
    def _ensure_parent(root: Path, path: Path) -> None:
        relative_parent = path.parent.relative_to(root)
        current = root
        for part in relative_parent.parts:
            current = current / part
            if current.is_symlink():
                raise PathEscape(f"symbolic link in destination parent: {current}")
            if current.exists() and not current.is_dir():
                raise InvalidLayer(f"parent is not a directory: {current}")
            current.mkdir(exist_ok=True, mode=0o755)

    def _apply_whiteouts(self, entries: list[_Entry], destination: Path) -> None:
        for entry in entries:
            if entry.whiteout == "opaque":
                parent = destination if len(entry.path.parts) == 1 else resolve_beneath(
                    destination, entry.path.parent
                )
                if parent.exists() and not parent.is_dir():
                    raise InvalidLayer(f"opaque whiteout parent is not a directory: {parent}")
                if parent.exists():
                    for child in list(parent.iterdir()):
                        self._remove(child)
            elif entry.whiteout == "remove":
                target_name = entry.path.name[len(".wh.") :]
                target_relative = entry.path.parent / target_name
                if entry.path.parent == PurePosixPath("."):
                    target_relative = PurePosixPath(target_name)
                target = resolve_beneath(destination, target_relative)
                self._remove(target)

    def _write_file(self, archive: tarfile.TarFile, entry: _Entry, target: Path) -> None:
        if target.is_symlink():
            raise PathEscape(f"symbolic link at file destination: {target}")
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists() and not target.is_file():
            raise InvalidLayer(f"special file at destination: {target}")

        source = archive.extractfile(entry.member)
        if source is None:
            raise InvalidLayer(f"missing payload for regular file: {entry.path}")
        descriptor, temporary_name = tempfile.mkstemp(prefix=".pydocklet-", dir=target.parent)
        temporary = Path(temporary_name)
        copied = 0
        try:
            with os.fdopen(descriptor, "wb") as output, source:
                while True:
                    chunk = source.read(self._COPY_CHUNK)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > entry.member.size:
                        raise InvalidLayer(f"payload is longer than declared size: {entry.path}")
                    output.write(chunk)
            if copied != entry.member.size:
                raise InvalidLayer(f"payload is shorter than declared size: {entry.path}")
            os.chmod(temporary, 0o755 if entry.member.mode & 0o111 else 0o644)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()

    def apply(self, archive_path: Path, destination: Path) -> None:
        archive_path = Path(archive_path)
        supplied_destination = Path(destination)
        if supplied_destination.is_symlink():
            raise InvalidLayer("layer destination must not be a symbolic link")
        destination = supplied_destination.resolve(strict=False)
        try:
            with tarfile.open(archive_path, mode="r:*") as archive:
                entries = self._read_and_preflight(archive)
                self._assert_regular_tree(destination)

                # Validate every existing target/parent before the first mutation.
                for entry in entries:
                    check = entry.path
                    if entry.whiteout == "remove":
                        check = entry.path.parent / entry.path.name[len(".wh.") :]
                        if entry.path.parent == PurePosixPath("."):
                            check = PurePosixPath(entry.path.name[len(".wh.") :])
                    elif entry.whiteout == "opaque":
                        check = entry.path.parent
                        if check == PurePosixPath("."):
                            continue
                    resolve_beneath(destination, check)

                destination.mkdir(parents=True, exist_ok=True, mode=0o755)
                self._apply_whiteouts(entries, destination)

                directories = [
                    entry for entry in entries if entry.whiteout is None and entry.member.isdir()
                ]
                files = [entry for entry in entries if entry.whiteout is None and entry.member.isfile()]

                for entry in sorted(directories, key=lambda item: len(item.path.parts)):
                    target = resolve_beneath(destination, entry.path)
                    self._ensure_parent(destination, target)
                    if target.exists() and not target.is_dir():
                        self._remove(target)
                    target.mkdir(exist_ok=True, mode=0o755)

                for entry in files:
                    target = resolve_beneath(destination, entry.path)
                    self._ensure_parent(destination, target)
                    self._write_file(archive, entry, target)

                for entry in directories:
                    os.chmod(resolve_beneath(destination, entry.path), 0o755)
        except (PathEscape, InvalidLayer):
            raise
        except (tarfile.TarError, OSError, EOFError) as exc:
            raise InvalidLayer(f"cannot apply layer {archive_path}: {exc}") from exc
