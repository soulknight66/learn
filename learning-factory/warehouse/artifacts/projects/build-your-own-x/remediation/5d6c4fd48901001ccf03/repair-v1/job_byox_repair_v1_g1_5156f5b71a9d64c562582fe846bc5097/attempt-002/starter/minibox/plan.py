"""Stage 3: turn policy into an inspectable namespace launch plan."""

from __future__ import annotations

from dataclasses import dataclass

from .config import ContainerSpec


@dataclass(frozen=True)
class IsolationPlan:
    """A deterministic description of requested namespaces and process argv."""

    namespaces: tuple[str, ...]
    argv: tuple[str, ...]


def build_plan(
    spec: ContainerSpec,
    *,
    unshare_path: str = "/usr/bin/unshare",
    python_path: str = "/usr/bin/python3",
) -> IsolationPlan:
    """Build, but do not execute, the Linux namespace command."""

    raise NotImplementedError("stage 3: implement build_plan")
