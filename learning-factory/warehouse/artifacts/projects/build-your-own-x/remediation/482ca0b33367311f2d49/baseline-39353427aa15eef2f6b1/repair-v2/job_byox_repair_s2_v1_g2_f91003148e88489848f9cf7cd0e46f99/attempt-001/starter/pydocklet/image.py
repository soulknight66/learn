"""Content-addressed image import (milestone 4)."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .layer import LayerApplier
from .models import ImageRecord
from .store import StateStore


class ImageStore:
    def __init__(self, root: Path, state: StateStore, applier: LayerApplier | None = None) -> None:
        self.root = Path(root)
        self.state = state
        self.applier = applier or LayerApplier()

    def import_image(self, name: str, layers: Sequence[Path]) -> ImageRecord:
        """TODO(4): validate, hash, build privately, publish, and register an image."""
        raise NotImplementedError("TODO(4): ImageStore.import_image")
