"""Coordination of image snapshots, durable claims, and process execution."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Mapping, Sequence

from .errors import InvalidLayer
from .image import ImageStore
from .models import ContainerRecord, ExecutionResult, ImageRecord
from .runner import ProcessRunner
from .store import StateStore


class Docklet:
    def __init__(self, root: Path, runner: ProcessRunner | None = None) -> None:
        self.root = Path(root)
        self.state = StateStore(self.root)
        self.root = self.state.root
        self.images = ImageStore(self.root, self.state)
        self.runner = runner or ProcessRunner()

    def import_image(self, name: str, layers: Sequence[Path]) -> ImageRecord:
        return self.images.import_image(name, layers)

    @staticmethod
    def _copy_regular_tree(source: Path, destination: Path) -> None:
        if source.is_symlink() or not source.is_dir():
            raise InvalidLayer("image rootfs is not a real directory")
        destination.mkdir(mode=0o755)
        pending: list[tuple[Path, Path]] = [(source, destination)]
        while pending:
            source_dir, destination_dir = pending.pop()
            for entry in os.scandir(source_dir):
                source_path = Path(entry.path)
                destination_path = destination_dir / entry.name
                if entry.is_symlink():
                    raise InvalidLayer(f"image contains a symbolic link: {source_path}")
                if entry.is_dir(follow_symlinks=False):
                    destination_path.mkdir(mode=0o755)
                    pending.append((source_path, destination_path))
                elif entry.is_file(follow_symlinks=False):
                    with source_path.open("rb") as input_file, destination_path.open("xb") as output_file:
                        shutil.copyfileobj(input_file, output_file, length=128 * 1024)
                    source_mode = source_path.stat(follow_symlinks=False).st_mode
                    os.chmod(destination_path, 0o755 if source_mode & 0o111 else 0o644)
                else:
                    raise InvalidLayer(f"image contains a special file: {source_path}")

    def create(
        self, image_name: str, command: Sequence[str], env: Mapping[str, str] | None = None
    ) -> ContainerRecord:
        image = self.state.get_image(image_name)
        self.images.verify(image)
        containers_root = self.root / "containers"
        containers_root.mkdir(exist_ok=True, mode=0o755)
        snapshot_dir = Path(tempfile.mkdtemp(prefix="snapshot-", dir=containers_root))
        rootfs = snapshot_dir / "rootfs"
        try:
            self._copy_regular_tree(image.rootfs, rootfs)
            return self.state.create_container(image.digest, command, env or {}, rootfs)
        except Exception:
            if snapshot_dir.exists():
                shutil.rmtree(snapshot_dir)
            raise

    def start(self, container_id: str, timeout: float = 5.0) -> ContainerRecord:
        claimed = self.state.claim_start(container_id)
        child_env = dict(claimed.env)
        child_env["PYDOCKLET_ROOT"] = str(claimed.rootfs)
        try:
            result = self.runner.run(claimed.command, claimed.rootfs, child_env, timeout)
        except Exception as exc:
            message = f"launch failed: {type(exc).__name__}: {exc}"
            result = ExecutionResult(125, "", message[: 64 * 1024], False)
        return self.state.finish(container_id, result)

    def inspect(self, container_id: str) -> ContainerRecord:
        return self.state.get_container(container_id)

    def list(self) -> list[ContainerRecord]:
        return self.state.list_containers()
