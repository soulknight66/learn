"""SQLite lifecycle state (milestone 3)."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from .models import ContainerRecord, ExecutionResult, ImageRecord


class StateStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.db_path = self.root / "state.sqlite3"
        self._initialize()

    def _initialize(self) -> None:
        """TODO(3): create the schema, transition rows, and enforcement trigger."""
        raise NotImplementedError("TODO(3): StateStore._initialize")

    def register_image(
        self, name: str, digest: str, rootfs: Path, layer_digests: Sequence[str]
    ) -> ImageRecord:
        raise NotImplementedError("TODO(3): StateStore.register_image")

    def get_image(self, name: str) -> ImageRecord:
        raise NotImplementedError("TODO(3): StateStore.get_image")

    def create_container(
        self,
        image_digest: str,
        command: Sequence[str],
        env: Mapping[str, str],
        rootfs: Path,
    ) -> ContainerRecord:
        raise NotImplementedError("TODO(3): StateStore.create_container")

    def get_container(self, container_id: str) -> ContainerRecord:
        raise NotImplementedError("TODO(3): StateStore.get_container")

    def list_containers(self) -> list[ContainerRecord]:
        raise NotImplementedError("TODO(3): StateStore.list_containers")

    def claim_start(self, container_id: str) -> ContainerRecord:
        raise NotImplementedError("TODO(3): StateStore.claim_start")

    def finish(self, container_id: str, result: ExecutionResult) -> ContainerRecord:
        raise NotImplementedError("TODO(3): StateStore.finish")
