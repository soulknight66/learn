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
    whiteout_target: PurePosixPath | None


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
            whiteout_target: PurePosixPath | None = None
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
                    target_name = safe_member_path(basename[len(".wh.") :])
                    if len(target_name.parts) != 1:
                        raise PathEscape(f"whiteout target must be one path component: {path}")
                    derived_target = (
                        target_name if path.parent == PurePosixPath(".") else path.parent / target_name
                    )
                    whiteout_target = safe_member_path(derived_target.as_posix())
            entries.append(_Entry(member, path, whiteout, whiteout_target))

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
    def _validated_destination(destination: Path) -> Path:
        """Return an absolute lexical path without adopting a symlink target."""

        try:
            candidate = Path(destination)
        except TypeError as exc:
            raise InvalidLayer("layer destination must be a filesystem path") from exc
        if ".." in candidate.parts:
            raise PathEscape("parent traversal is forbidden in the layer destination")

        absolute = Path(os.path.abspath(os.fspath(candidate)))
        current = Path(absolute.anchor)
        parts = absolute.parts[1:]
        for index, part in enumerate(parts):
            current = current / part
            try:
                mode = current.lstat().st_mode
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise InvalidLayer(f"cannot inspect destination ancestry: {exc}") from exc
            if stat.S_ISLNK(mode):
                raise PathEscape(f"symbolic link in supplied destination ancestry: {current}")
            if index < len(parts) - 1 and not stat.S_ISDIR(mode):
                raise InvalidLayer(f"destination ancestor is not a directory: {current}")
        return absolute

    @staticmethod
    def _remove_type_subtree(types: dict[PurePosixPath, str], target: PurePosixPath) -> None:
        for path in list(types):
            if path == target or target in path.parents:
                del types[path]

    @staticmethod
    def _check_parent_types(
        types: dict[PurePosixPath, str], path: PurePosixPath, *, create: bool
    ) -> None:
        current = PurePosixPath()
        for part in path.parts[:-1]:
            current = current / part
            observed = types.get(current)
            if observed == "file":
                raise InvalidLayer(f"parent is not a directory: {current}")
            if observed is None and create:
                types[current] = "directory"

    def _preflight_destination(self, entries: list[_Entry], destination: Path) -> None:
        """Simulate type changes so whiteouts cannot precede a deterministic failure."""

        types: dict[PurePosixPath, str] = {}
        if destination.exists():
            pending: list[tuple[Path, PurePosixPath]] = [
                (destination, PurePosixPath("."))
            ]
            while pending:
                directory, relative = pending.pop()
                try:
                    children = list(os.scandir(directory))
                except OSError as exc:
                    raise InvalidLayer(f"cannot inspect destination: {exc}") from exc
                for child in children:
                    child_relative = (
                        PurePosixPath(child.name)
                        if relative == PurePosixPath(".")
                        else relative / child.name
                    )
                    if child.is_dir(follow_symlinks=False):
                        types[child_relative] = "directory"
                        pending.append((Path(child.path), child_relative))
                    elif child.is_file(follow_symlinks=False):
                        types[child_relative] = "file"
                    else:
                        raise InvalidLayer(f"destination contains a non-regular entry: {child.path}")

        for entry in entries:
            if entry.whiteout == "opaque":
                parent = entry.path.parent
                if parent == PurePosixPath("."):
                    types.clear()
                    continue
                self._check_parent_types(types, parent / "child", create=False)
                if types.get(parent) == "file":
                    raise InvalidLayer(f"opaque whiteout parent is not a directory: {parent}")
                if types.get(parent) == "directory":
                    for path in list(types):
                        if parent in path.parents:
                            del types[path]
            elif entry.whiteout == "remove":
                if entry.whiteout_target is None:
                    raise InvalidLayer(f"whiteout target was not preflighted: {entry.path}")
                target = entry.whiteout_target
                self._check_parent_types(types, target, create=False)
                self._remove_type_subtree(types, target)

        directories = sorted(
            (entry for entry in entries if entry.whiteout is None and entry.member.isdir()),
            key=lambda item: len(item.path.parts),
        )
        for entry in directories:
            self._check_parent_types(types, entry.path, create=True)
            if types.get(entry.path) == "file":
                self._remove_type_subtree(types, entry.path)
            types[entry.path] = "directory"

        for entry in entries:
            if entry.whiteout is not None or not entry.member.isfile():
                continue
            self._check_parent_types(types, entry.path, create=True)
            if types.get(entry.path) == "directory":
                self._remove_type_subtree(types, entry.path)
            types[entry.path] = "file"

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
            os.chmod(current, 0o755)

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
                if entry.whiteout_target is None:
                    raise InvalidLayer(f"whiteout target was not preflighted: {entry.path}")
                target = resolve_beneath(destination, entry.whiteout_target)
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
        destination = self._validated_destination(destination)
        try:
            with tarfile.open(archive_path, mode="r:*") as archive:
                entries = self._read_and_preflight(archive)
                self._assert_regular_tree(destination)
                self._preflight_destination(entries, destination)

                destination.mkdir(parents=True, exist_ok=True, mode=0o755)
                os.chmod(destination, 0o755)
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
