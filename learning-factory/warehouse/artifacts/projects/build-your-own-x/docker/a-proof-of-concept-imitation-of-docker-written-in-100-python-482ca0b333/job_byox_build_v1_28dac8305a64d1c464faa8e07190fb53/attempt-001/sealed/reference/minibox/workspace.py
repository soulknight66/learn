"""Filesystem ownership and integration facade."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Iterator

from .archive import LayerStats, apply_layer
from .errors import ContainerExists, ImageExists, ImageNotFound, InvalidSpec, StateCorruption
from .models import ContainerSpec, validate_identifier
from .state import ContainerRecord, StateStore


class Workspace:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).absolute()
        if os.path.lexists(self.root) and stat.S_ISLNK(self.root.lstat().st_mode):
            raise StateCorruption(f"workspace root must not be a symlink: {self.root}")
        self.root.mkdir(parents=True, exist_ok=True)
        self.images = self.root / "images"
        self.containers = self.root / "containers"
        self.images.mkdir(exist_ok=True)
        self.containers.mkdir(exist_ok=True)
        (self.images / ".locks").mkdir(exist_ok=True)
        (self.containers / ".locks").mkdir(exist_ok=True)
        self.state = StateStore(self.root / "state.sqlite3")

    @contextmanager
    def _lock(self, parent: Path, identifier: str) -> Iterator[None]:
        lock_path = parent / ".locks" / f"{identifier}.lock"
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def import_image(self, image_id: str, layer_path: str | Path) -> LayerStats:
        canonical_id = validate_identifier(image_id)
        layer = Path(layer_path)
        if not layer.is_file() or layer.is_symlink():
            raise InvalidSpec(f"layer must be a regular file: {layer}")
        destination = self.images / canonical_id

        with self._lock(self.images, canonical_id):
            if os.path.lexists(destination):
                raise ImageExists(f"image already exists: {canonical_id}")
            staging = Path(tempfile.mkdtemp(prefix=f".import-{canonical_id}-", dir=self.images))
            published = False
            try:
                rootfs = staging / "rootfs"
                stats = apply_layer(layer, rootfs)
                manifest = {
                    "image_id": canonical_id,
                    "layer_sha256": self._sha256(layer),
                    "provenance": {"kind": "local-layer-tar"},
                    "schema_version": 1,
                    "stats": asdict(stats),
                    "validation_labels": ["ARCHIVE_VALIDATED", "NOT_EXECUTED"],
                }
                manifest_path = staging / "manifest.json"
                with manifest_path.open("w", encoding="utf-8") as output:
                    json.dump(manifest, output, sort_keys=True, separators=(",", ":"))
                    output.write("\n")
                    output.flush()
                    os.fsync(output.fileno())
                os.rename(staging, destination)
                published = True
                return stats
            finally:
                if not published and staging.exists():
                    shutil.rmtree(staging)

    def create(self, spec: ContainerSpec) -> ContainerRecord:
        if not isinstance(spec, ContainerSpec):
            raise TypeError("spec must be a ContainerSpec")
        image_rootfs = self.images / spec.image_id / "rootfs"
        if not image_rootfs.is_dir() or image_rootfs.is_symlink():
            raise ImageNotFound(f"image does not exist: {spec.image_id}")
        destination = self.containers / spec.container_id

        with self._lock(self.containers, spec.container_id):
            if os.path.lexists(destination):
                raise ContainerExists(f"container already exists: {spec.container_id}")
            staging = Path(
                tempfile.mkdtemp(prefix=f".create-{spec.container_id}-", dir=self.containers)
            )
            published = False
            try:
                shutil.copytree(image_rootfs, staging / "rootfs")
                os.rename(staging, destination)
                published = True
                try:
                    return self.state.create(spec)
                except Exception:
                    shutil.rmtree(destination)
                    published = False
                    raise
            finally:
                if not published and staging.exists():
                    shutil.rmtree(staging)

    def rootfs_for(self, container_id: str) -> Path:
        canonical_id = validate_identifier(container_id)
        self.state.get(canonical_id)
        rootfs = self.containers / canonical_id / "rootfs"
        try:
            mode = rootfs.lstat().st_mode
        except OSError as exc:
            raise StateCorruption(f"container rootfs is missing: {canonical_id}") from exc
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise StateCorruption(f"container rootfs is invalid: {canonical_id}")
        return rootfs
