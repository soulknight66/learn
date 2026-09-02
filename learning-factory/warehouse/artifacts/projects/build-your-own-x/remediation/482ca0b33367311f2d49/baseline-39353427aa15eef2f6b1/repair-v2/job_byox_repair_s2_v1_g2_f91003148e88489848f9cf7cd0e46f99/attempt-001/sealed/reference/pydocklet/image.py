"""Content-addressed image import and atomic publication."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Sequence

import fcntl

from .errors import Conflict, InvalidLayer, InvalidName, NotFound
from .layer import LayerApplier
from .models import ImageRecord
from .store import StateStore


_NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}\Z")
_BUFFER = 256 * 1024


class ImageStore:
    def __init__(self, root: Path, state: StateStore, applier: LayerApplier | None = None) -> None:
        self.root = Path(root).resolve(strict=False)
        self.state = state
        self.applier = applier or LayerApplier()
        self.images_root = self.root / "images"
        self.images_root.mkdir(parents=True, exist_ok=True, mode=0o755)
        self.locks_root = self.root / ".image-locks"
        self.locks_root.mkdir(parents=True, exist_ok=True, mode=0o700)

    @staticmethod
    def _hash_layer(path: Path) -> str:
        if path.is_symlink() or not path.is_file():
            raise InvalidLayer(f"layer is not a regular file: {path}")
        digest = hashlib.sha256()
        try:
            with path.open("rb") as source:
                while True:
                    chunk = source.read(_BUFFER)
                    if not chunk:
                        break
                    digest.update(chunk)
        except OSError as exc:
            raise InvalidLayer(f"cannot read layer {path}: {exc}") from exc
        return f"sha256:{digest.hexdigest()}"

    @staticmethod
    def _image_digest(layer_digests: tuple[str, ...]) -> str:
        descriptor = json.dumps(
            {"layers": layer_digests, "schema": 1},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(descriptor).hexdigest()}"

    @staticmethod
    def _manifest_bytes(
        digest: str, layers: tuple[str, ...], rootfs_digest: str
    ) -> bytes:
        return (
            json.dumps(
                {
                    "digest": digest,
                    "layers": layers,
                    "rootfs_digest": rootfs_digest,
                    "schema": 1,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")

    @staticmethod
    def _stage_layer(source_path: Path, destination: Path) -> str:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(source_path, flags)
        except OSError as exc:
            raise InvalidLayer(f"cannot open layer {source_path}: {exc}") from exc

        digest = hashlib.sha256()
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise InvalidLayer(f"layer is not a regular file: {source_path}")
            with os.fdopen(descriptor, "rb") as source, destination.open("xb") as output:
                descriptor = -1
                while True:
                    chunk = source.read(_BUFFER)
                    if not chunk:
                        break
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        except InvalidLayer:
            raise
        except OSError as exc:
            raise InvalidLayer(f"cannot stage layer {source_path}: {exc}") from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        return f"sha256:{digest.hexdigest()}"

    @contextmanager
    def _import_lock(self, digest_hex: str):
        if self.locks_root.is_symlink() or not self.locks_root.is_dir():
            raise Conflict("image lock root is not a real directory")
        lock_path = self.locks_root / digest_hex
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = -1
        try:
            descriptor = os.open(lock_path, flags, 0o600)
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise Conflict("image import lock is not a regular file")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        except Conflict:
            if descriptor >= 0:
                os.close(descriptor)
            raise
        except OSError as exc:
            if descriptor >= 0:
                os.close(descriptor)
            raise Conflict(f"cannot acquire image import lock: {exc}") from exc
        try:
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    @staticmethod
    def _freeze_tree(rootfs: Path) -> None:
        pending = [rootfs]
        directories: list[Path] = []
        while pending:
            directory = pending.pop()
            directories.append(directory)
            for entry in os.scandir(directory):
                path = Path(entry.path)
                if entry.is_symlink():
                    raise InvalidLayer(f"image contains a symbolic link: {path}")
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    mode = entry.stat(follow_symlinks=False).st_mode
                    os.chmod(path, 0o555 if mode & 0o111 else 0o444)
                else:
                    raise InvalidLayer(f"image contains a special file: {path}")
        for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
            os.chmod(directory, 0o555)

    @staticmethod
    def _rootfs_digest(rootfs: Path) -> str:
        try:
            root_mode = stat.S_IMODE(rootfs.stat(follow_symlinks=False).st_mode)
        except OSError as exc:
            raise Conflict(f"cannot inspect published image rootfs: {exc}") from exc
        if rootfs.is_symlink() or not rootfs.is_dir() or root_mode != 0o555:
            raise Conflict("published image rootfs is not a read-only real directory")

        records: list[dict[str, object]] = []
        pending: list[tuple[Path, str]] = [(rootfs, "")]
        while pending:
            directory, prefix = pending.pop()
            try:
                children = sorted(os.scandir(directory), key=lambda entry: entry.name)
            except OSError as exc:
                raise Conflict(f"cannot inspect published image rootfs: {exc}") from exc
            for entry in children:
                relative = f"{prefix}/{entry.name}" if prefix else entry.name
                path = Path(entry.path)
                if entry.is_symlink():
                    raise Conflict(f"published image contains a symbolic link: {relative}")
                metadata = entry.stat(follow_symlinks=False)
                mode = stat.S_IMODE(metadata.st_mode)
                if entry.is_dir(follow_symlinks=False):
                    if mode != 0o555:
                        raise Conflict(f"published image directory is writable: {relative}")
                    records.append({"mode": mode, "path": relative, "type": "directory"})
                    pending.append((path, relative))
                elif entry.is_file(follow_symlinks=False):
                    if mode not in (0o444, 0o555):
                        raise Conflict(f"published image file has mutable mode: {relative}")
                    file_digest = hashlib.sha256()
                    try:
                        with path.open("rb") as source:
                            while True:
                                chunk = source.read(_BUFFER)
                                if not chunk:
                                    break
                                file_digest.update(chunk)
                    except OSError as exc:
                        raise Conflict(f"cannot read published image file {relative}: {exc}") from exc
                    records.append(
                        {
                            "mode": mode,
                            "path": relative,
                            "sha256": file_digest.hexdigest(),
                            "size": metadata.st_size,
                            "type": "file",
                        }
                    )
                else:
                    raise Conflict(f"published image contains a special file: {relative}")

        descriptor = json.dumps(
            sorted(records, key=lambda record: str(record["path"])),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(descriptor).hexdigest()}"

    @staticmethod
    def _remove_tree(path: Path) -> None:
        if not path.exists() and not path.is_symlink():
            return
        if path.is_symlink() or not path.is_dir():
            path.unlink()
            return
        for directory, names, _ in os.walk(path):
            os.chmod(directory, 0o700)
            for name in names:
                child = Path(directory) / name
                if child.is_dir() and not child.is_symlink():
                    os.chmod(child, 0o700)
        shutil.rmtree(path)

    def _verify_published(self, image_dir: Path, digest: str, layers: tuple[str, ...]) -> None:
        if image_dir.is_symlink() or not image_dir.is_dir():
            raise Conflict(f"published image path is not a directory: {image_dir}")
        if stat.S_IMODE(image_dir.stat(follow_symlinks=False).st_mode) != 0o555:
            raise Conflict(f"published image directory has mutable mode: {digest}")
        manifest = image_dir / "manifest.json"
        if manifest.is_symlink() or not manifest.is_file():
            raise Conflict(f"published image manifest is missing: {digest}")
        if stat.S_IMODE(manifest.stat(follow_symlinks=False).st_mode) != 0o444:
            raise Conflict(f"published image manifest has mutable mode: {digest}")
        try:
            observed = manifest.read_bytes()
        except OSError as exc:
            raise Conflict(f"cannot read published image manifest: {exc}") from exc
        rootfs = image_dir / "rootfs"
        if rootfs.is_symlink() or not rootfs.is_dir():
            raise Conflict(f"published image rootfs is missing: {digest}")
        rootfs_digest = self._rootfs_digest(rootfs)
        if observed != self._manifest_bytes(digest, layers, rootfs_digest):
            raise Conflict(f"published image metadata does not match content: {digest}")

    def verify(self, record: ImageRecord) -> None:
        digest_hex = record.digest.removeprefix("sha256:")
        image_dir = self.images_root / digest_hex
        expected_rootfs = image_dir / "rootfs"
        if record.rootfs != expected_rootfs:
            raise Conflict("persisted image rootfs does not match its content address")
        self._verify_published(image_dir, record.digest, record.layer_digests)

    def import_image(self, name: str, layers: Sequence[Path]) -> ImageRecord:
        if not isinstance(name, str) or not _NAME.fullmatch(name):
            raise InvalidName(f"invalid image name: {name!r}")
        if isinstance(layers, (str, bytes)):
            raise InvalidLayer("layers must be a sequence of paths")
        layer_paths = tuple(Path(path) for path in layers)
        if not layer_paths:
            raise InvalidLayer("an image requires at least one layer")

        staging_dir = Path(tempfile.mkdtemp(prefix=".staged-", dir=self.images_root))
        build_dir: Path | None = None
        try:
            staged_layers: list[Path] = []
            layer_digest_values: list[str] = []
            for index, layer_path in enumerate(layer_paths):
                staged_path = staging_dir / f"{index:08d}.layer"
                layer_digest_values.append(self._stage_layer(layer_path, staged_path))
                staged_layers.append(staged_path)
            layer_digests = tuple(layer_digest_values)
            digest = self._image_digest(layer_digests)
            digest_hex = digest.removeprefix("sha256:")
            image_dir = self.images_root / digest_hex
            rootfs = image_dir / "rootfs"
            published_by_this_call = False

            with self._import_lock(digest_hex):
                try:
                    try:
                        existing = self.state.get_image(name)
                    except NotFound:
                        existing = None
                    if existing is not None:
                        if existing.digest != digest:
                            raise Conflict(
                                f"image tag is already bound to different content: {name}"
                            )
                        self._verify_published(image_dir, digest, layer_digests)
                        return existing

                    if not image_dir.exists():
                        build_dir = Path(
                            tempfile.mkdtemp(prefix=".build-", dir=self.images_root)
                        )
                        build_rootfs = build_dir / "rootfs"
                        for staged_path in staged_layers:
                            self.applier.apply(staged_path, build_rootfs)
                        self._freeze_tree(build_rootfs)
                        rootfs_digest = self._rootfs_digest(build_rootfs)
                        manifest = build_dir / "manifest.json"
                        descriptor = os.open(
                            manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                        )
                        with os.fdopen(descriptor, "wb") as output:
                            output.write(
                                self._manifest_bytes(digest, layer_digests, rootfs_digest)
                            )
                            output.flush()
                            os.fsync(output.fileno())
                        os.chmod(manifest, 0o444)
                        os.chmod(build_dir, 0o555)
                        os.rename(build_dir, image_dir)
                        build_dir = None
                        published_by_this_call = True

                    self._verify_published(image_dir, digest, layer_digests)
                    return self.state.register_image(name, digest, rootfs, layer_digests)
                except Exception:
                    if published_by_this_call:
                        try:
                            unreferenced = not self.state.has_image_object(digest)
                        except Exception:
                            unreferenced = False
                        if unreferenced:
                            self._remove_tree(image_dir)
                    raise
        finally:
            if build_dir is not None and build_dir.exists():
                self._remove_tree(build_dir)
            self._remove_tree(staging_dir)
