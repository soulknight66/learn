"""Content-addressed image import and atomic publication."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Sequence

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
    def _manifest_bytes(digest: str, layers: tuple[str, ...]) -> bytes:
        return (
            json.dumps(
                {"digest": digest, "layers": layers, "schema": 1},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")

    def _verify_published(self, image_dir: Path, digest: str, layers: tuple[str, ...]) -> None:
        if image_dir.is_symlink() or not image_dir.is_dir():
            raise Conflict(f"published image path is not a directory: {image_dir}")
        manifest = image_dir / "manifest.json"
        if manifest.is_symlink() or not manifest.is_file():
            raise Conflict(f"published image manifest is missing: {digest}")
        try:
            observed = manifest.read_bytes()
        except OSError as exc:
            raise Conflict(f"cannot read published image manifest: {exc}") from exc
        if observed != self._manifest_bytes(digest, layers):
            raise Conflict(f"published image metadata does not match digest: {digest}")
        rootfs = image_dir / "rootfs"
        if rootfs.is_symlink() or not rootfs.is_dir():
            raise Conflict(f"published image rootfs is missing: {digest}")
        self.applier._assert_regular_tree(rootfs)

    def import_image(self, name: str, layers: Sequence[Path]) -> ImageRecord:
        if not isinstance(name, str) or not _NAME.fullmatch(name):
            raise InvalidName(f"invalid image name: {name!r}")
        if isinstance(layers, (str, bytes)):
            raise InvalidLayer("layers must be a sequence of paths")
        layer_paths = tuple(Path(path) for path in layers)
        if not layer_paths:
            raise InvalidLayer("an image requires at least one layer")

        layer_digests = tuple(self._hash_layer(path) for path in layer_paths)
        digest = self._image_digest(layer_digests)
        digest_hex = digest.removeprefix("sha256:")
        image_dir = self.images_root / digest_hex
        rootfs = image_dir / "rootfs"

        try:
            existing = self.state.get_image(name)
        except NotFound:
            existing = None
        if existing is not None:
            if existing.digest != digest:
                raise Conflict(f"image tag is already bound to different content: {name}")
            self._verify_published(image_dir, digest, layer_digests)
            return existing

        build_dir: Path | None = None
        try:
            if not image_dir.exists():
                build_dir = Path(tempfile.mkdtemp(prefix=".build-", dir=self.images_root))
                build_rootfs = build_dir / "rootfs"
                for layer_path in layer_paths:
                    self.applier.apply(layer_path, build_rootfs)
                manifest = build_dir / "manifest.json"
                descriptor = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
                with os.fdopen(descriptor, "wb") as output:
                    output.write(self._manifest_bytes(digest, layer_digests))
                    output.flush()
                    os.fsync(output.fileno())
                try:
                    os.rename(build_dir, image_dir)
                    build_dir = None
                except FileExistsError:
                    # Another importer published identical content. Its manifest is verified below.
                    pass

            self._verify_published(image_dir, digest, layer_digests)
            return self.state.register_image(name, digest, rootfs, layer_digests)
        finally:
            if build_dir is not None and build_dir.exists():
                shutil.rmtree(build_dir)
