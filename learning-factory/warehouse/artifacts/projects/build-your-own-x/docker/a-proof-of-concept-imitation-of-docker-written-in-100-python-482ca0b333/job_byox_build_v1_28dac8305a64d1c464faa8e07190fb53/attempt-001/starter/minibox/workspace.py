"""Filesystem ownership and integration facade."""

from __future__ import annotations

from pathlib import Path

from .archive import LayerStats
from .models import ContainerSpec
from .state import ContainerRecord, StateStore


class Workspace:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.images = self.root / "images"
        self.containers = self.root / "containers"
        self.state = StateStore(self.root / "state.sqlite3")

    def import_image(self, image_id: str, layer_path: str | Path) -> LayerStats:
        raise NotImplementedError("milestone 5: stage and atomically publish an image")

    def create(self, spec: ContainerSpec) -> ContainerRecord:
        raise NotImplementedError("milestone 5: materialize a writable container rootfs")

    def rootfs_for(self, container_id: str) -> Path:
        raise NotImplementedError("milestone 5: resolve an owned rootfs")
