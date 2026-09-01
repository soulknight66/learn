"""Safe, streaming application of a single container filesystem layer."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tarfile
import tempfile

from .errors import InvalidArchive


@dataclass(frozen=True)
class LayerLimits:
    max_members: int = 10_000
    max_file_size: int = 64 * 1024 * 1024
    max_total_size: int = 256 * 1024 * 1024

    def __post_init__(self) -> None:
        for name, value in (
            ("max_members", self.max_members),
            ("max_file_size", self.max_file_size),
            ("max_total_size", self.max_total_size),
        ):
            if type(value) is not int or value < 0:
                raise InvalidArchive(f"{name} must be a non-negative integer")


@dataclass(frozen=True)
class LayerStats:
    files_written: int
    directories_created: int
    whiteouts_applied: int
    bytes_written: int


@dataclass(frozen=True)
class _ValidatedMember:
    info: tarfile.TarInfo
    path: PurePosixPath
    whiteout: str | None


def safe_member_path(name: str) -> PurePosixPath:
    """Normalize one tar name without allowing it to address outside rootfs."""
    if not isinstance(name, str) or not name or "\x00" in name or "\\" in name:
        raise InvalidArchive(f"unsafe archive member name: {name!r}")
    if name.startswith("/"):
        raise InvalidArchive(f"absolute archive member name: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise InvalidArchive(f"archive member escapes rootfs: {name!r}")
    useful_parts = tuple(part for part in path.parts if part not in ("", "."))
    if not useful_parts:
        raise InvalidArchive(f"archive member has no destination: {name!r}")
    return PurePosixPath(*useful_parts)


def _lexists(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _reject_symlinked_root(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if not _lexists(current):
            continue
        mode = current.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise InvalidArchive(f"rootfs path contains a symlink: {current}")
        if current != absolute and not stat.S_ISDIR(mode):
            raise InvalidArchive(f"rootfs parent is not a directory: {current}")
    if _lexists(absolute) and not absolute.is_dir():
        raise InvalidArchive(f"rootfs is not a directory: {absolute}")


def _preflight_existing_path(root: Path, relative: PurePosixPath) -> None:
    current = root
    for part in relative.parts:
        current /= part
        if not _lexists(current):
            continue
        mode = current.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise InvalidArchive(f"destination contains a symlink: {relative}")
        if not stat.S_ISDIR(mode):
            # A layer may replace this leaf with a directory before adding children.
            break


def _remove_path(path: Path) -> None:
    if not _lexists(path):
        return
    mode = path.lstat().st_mode
    if stat.S_ISDIR(mode) and not stat.S_ISLNK(mode):
        shutil.rmtree(path)
    else:
        path.unlink()


def _ensure_directory(root: Path, relative: PurePosixPath) -> int:
    created = 0
    current = root
    for part in relative.parts:
        current /= part
        if _lexists(current):
            mode = current.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise InvalidArchive(f"refusing to follow destination symlink: {relative}")
            if stat.S_ISDIR(mode):
                continue
            _remove_path(current)
        current.mkdir(mode=0o755)
        created += 1
    return created


def _validate_members(archive: tarfile.TarFile, limits: LayerLimits) -> list[_ValidatedMember]:
    members = archive.getmembers()
    if len(members) > limits.max_members:
        raise InvalidArchive(f"archive has {len(members)} members; limit is {limits.max_members}")

    validated: list[_ValidatedMember] = []
    destinations: set[PurePosixPath] = set()
    total_size = 0
    for member in members:
        relative = safe_member_path(member.name)
        if relative in destinations:
            raise InvalidArchive(f"duplicate normalized destination: {relative}")
        destinations.add(relative)

        if member.size < 0:
            raise InvalidArchive(f"negative member size: {relative}")
        if member.isfile():
            if member.size > limits.max_file_size:
                raise InvalidArchive(f"member exceeds file-size limit: {relative}")
            total_size += member.size
            if total_size > limits.max_total_size:
                raise InvalidArchive("archive exceeds total-size limit")
        elif not member.isdir():
            raise InvalidArchive(f"unsupported member type for {relative}")

        whiteout: str | None = None
        if relative.name.startswith(".wh."):
            if not member.isfile() or member.size != 0:
                raise InvalidArchive(f"whiteout must be an empty regular file: {relative}")
            if relative.name == ".wh..wh..opq":
                whiteout = "opaque"
            elif relative.name == ".wh.":
                raise InvalidArchive(f"whiteout has no target: {relative}")
            else:
                whiteout = relative.name[4:]
                if whiteout in (".", ".."):
                    raise InvalidArchive(f"whiteout has an unsafe target: {relative}")
        validated.append(_ValidatedMember(member, relative, whiteout))
    return validated


def apply_layer(
    layer_path: str | Path,
    rootfs: str | Path,
    *,
    limits: LayerLimits | None = None,
) -> LayerStats:
    """Validate and apply one tar layer without following links."""
    active_limits = limits if limits is not None else LayerLimits()
    if not isinstance(active_limits, LayerLimits):
        raise InvalidArchive("limits must be a LayerLimits instance")
    root = Path(rootfs).absolute()

    try:
        archive_context = tarfile.open(Path(layer_path), mode="r:*")
    except (OSError, tarfile.TarError) as exc:
        raise InvalidArchive(f"cannot open layer archive: {exc}") from exc

    with archive_context as archive:
        try:
            members = _validate_members(archive, active_limits)
        except (OSError, tarfile.TarError) as exc:
            raise InvalidArchive(f"cannot read layer metadata: {exc}") from exc

        _reject_symlinked_root(root)
        for member in members:
            check_path = member.path.parent if member.whiteout is not None else member.path
            if check_path.parts:
                _preflight_existing_path(root, check_path)

        root.mkdir(parents=True, exist_ok=True)
        directories_created = 0
        whiteouts_applied = 0

        # Whiteouts describe the lower layer, so apply them before new payload entries.
        for member in members:
            if member.whiteout is None:
                continue
            parent_relative = member.path.parent
            directories_created += _ensure_directory(root, parent_relative)
            parent = root.joinpath(*parent_relative.parts)
            if member.whiteout == "opaque":
                for child in list(parent.iterdir()):
                    _remove_path(child)
            else:
                _remove_path(parent / member.whiteout)
            whiteouts_applied += 1

        directory_members = sorted(
            (item for item in members if item.whiteout is None and item.info.isdir()),
            key=lambda item: len(item.path.parts),
        )
        for member in directory_members:
            directories_created += _ensure_directory(root, member.path)

        files_written = 0
        bytes_written = 0
        for member in (item for item in members if item.whiteout is None and item.info.isfile()):
            directories_created += _ensure_directory(root, member.path.parent)
            destination = root.joinpath(*member.path.parts)
            if _lexists(destination):
                if stat.S_ISLNK(destination.lstat().st_mode):
                    raise InvalidArchive(f"refusing to replace destination symlink: {member.path}")
                _remove_path(destination)

            source = archive.extractfile(member.info)
            if source is None:
                raise InvalidArchive(f"regular member has no payload: {member.path}")
            temporary_name: str | None = None
            copied = 0
            try:
                with source, tempfile.NamedTemporaryFile(
                    mode="wb", prefix=".minibox-layer-", dir=destination.parent, delete=False
                ) as output:
                    temporary_name = output.name
                    while True:
                        chunk = source.read(64 * 1024)
                        if not chunk:
                            break
                        copied += len(chunk)
                        if copied > member.info.size:
                            raise InvalidArchive(f"payload exceeds declared size: {member.path}")
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
                if copied != member.info.size:
                    raise InvalidArchive(f"payload shorter than declared size: {member.path}")
                os.chmod(temporary_name, member.info.mode & 0o777)
                os.replace(temporary_name, destination)
                temporary_name = None
            except (OSError, tarfile.TarError) as exc:
                raise InvalidArchive(f"cannot extract {member.path}: {exc}") from exc
            finally:
                if temporary_name is not None and os.path.exists(temporary_name):
                    os.unlink(temporary_name)
            files_written += 1
            bytes_written += copied

        # Set directory modes only after children are materialized; a valid layer
        # may intentionally make a directory non-writable or non-searchable.
        for member in reversed(directory_members):
            destination = root.joinpath(*member.path.parts)
            os.chmod(destination, member.info.mode & 0o777)

    return LayerStats(files_written, directories_created, whiteouts_applied, bytes_written)
