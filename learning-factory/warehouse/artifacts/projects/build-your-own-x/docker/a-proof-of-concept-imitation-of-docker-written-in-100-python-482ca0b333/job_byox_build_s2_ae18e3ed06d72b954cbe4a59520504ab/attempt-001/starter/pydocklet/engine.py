"""High-level orchestration (milestone 6)."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from .image import ImageStore
from .models import ContainerRecord, ImageRecord
from .runner import ProcessRunner
from .store import StateStore


class Docklet:
    def __init__(self, root: Path, runner: ProcessRunner | None = None) -> None:
        self.root = Path(root)
        self.state = StateStore(self.root)
        self.images = ImageStore(self.root, self.state)
        self.runner = runner or ProcessRunner()

    def import_image(self, name: str, layers: Sequence[Path]) -> ImageRecord:
        return self.images.import_image(name, layers)

    def create(
        self, image_name: str, command: Sequence[str], env: Mapping[str, str] | None = None
    ) -> ContainerRecord:
        """TODO(6): copy a rootfs without links and persist a CREATED record."""
        raise NotImplementedError("TODO(6): Docklet.create")

    def start(self, container_id: str, timeout: float = 5.0) -> ContainerRecord:
        """TODO(6): atomically claim, run, and always finish a claimed record."""
        raise NotImplementedError("TODO(6): Docklet.start")

    def inspect(self, container_id: str) -> ContainerRecord:
        return self.state.get_container(container_id)

    def list(self) -> list[ContainerRecord]:
        return self.state.list_containers()
