"""Stage 1: parse an intentionally small, closed container specification."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .errors import SpecError


@dataclass(frozen=True)
class ContainerSpec:
    """Validated input used by every later Minibox stage."""

    schema_version: int
    rootfs: Path
    argv: tuple[str, ...]
    env: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({})
    )
    hostname: str = "minibox"
    network_mode: str = "none"
    timeout_seconds: float = 30.0


def from_dict(data: Mapping[str, Any]) -> ContainerSpec:
    """Validate *data* and return an immutable specification.

    Implement the contract in REQUIREMENTS.md.  In particular, do not silently
    retain unknown keys or rely on truthiness for JSON type checks.
    """

    raise NotImplementedError("stage 1: implement from_dict")


def load_spec(path: str | Path) -> ContainerSpec:
    """Load one UTF-8 JSON object and delegate validation to ``from_dict``."""

    raise NotImplementedError("stage 1: implement load_spec")
