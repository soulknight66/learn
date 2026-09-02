"""Safe tar layer application (milestone 2)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LayerLimits:
    max_members: int = 1024
    max_file_bytes: int = 8 * 1024 * 1024
    max_total_bytes: int = 32 * 1024 * 1024

    def __post_init__(self) -> None:
        if self.max_members < 1 or self.max_file_bytes < 0 or self.max_total_bytes < 0:
            raise ValueError("layer limits must be non-negative and allow at least one member")


class LayerApplier:
    def __init__(self, limits: LayerLimits | None = None) -> None:
        self.limits = limits or LayerLimits()

    def apply(self, archive_path: Path, destination: Path) -> None:
        """Apply one validated tar layer to *destination*.

        TODO(2): split this into a no-mutation preflight and a streaming apply phase. Do not call
        TarFile.extract or extractall.
        """
        raise NotImplementedError("TODO(2): LayerApplier.apply")
