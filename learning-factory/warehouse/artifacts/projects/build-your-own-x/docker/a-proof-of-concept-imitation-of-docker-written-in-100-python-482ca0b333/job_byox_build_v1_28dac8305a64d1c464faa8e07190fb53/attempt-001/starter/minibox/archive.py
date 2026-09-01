"""Safe, streaming application of a single container filesystem layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class LayerLimits:
    max_members: int = 10_000
    max_file_size: int = 64 * 1024 * 1024
    max_total_size: int = 256 * 1024 * 1024


@dataclass(frozen=True)
class LayerStats:
    files_written: int
    directories_created: int
    whiteouts_applied: int
    bytes_written: int


def safe_member_path(name: str) -> PurePosixPath:
    """Normalize one tar name without allowing it to address outside rootfs."""
    raise NotImplementedError("milestone 2: normalize and validate member paths")


def apply_layer(
    layer_path: str | Path,
    rootfs: str | Path,
    *,
    limits: LayerLimits | None = None,
) -> LayerStats:
    """Validate and apply one tar layer without following links."""
    raise NotImplementedError("milestone 2: implement safe layer application")
