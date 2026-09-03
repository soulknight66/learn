"""Compile a validated spec into an inert process launch plan."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .spec import ContainerSpec


@dataclass(frozen=True, slots=True)
class LaunchPlan:
    argv: tuple[str, ...]
    helper_env_items: tuple[tuple[str, str], ...]
    timeout_seconds: float

    @property
    def helper_env(self) -> Mapping[str, str]:
        return dict(self.helper_env_items)


def build_launch_plan(spec: ContainerSpec, unshare_path: str) -> LaunchPlan:
    """Return an immutable, shell-free launch plan satisfying requirement R3."""
    # TODO(stage 3): validate the executable and rootfs, then construct every namespace flag.
    # Keep the workload command and environment out of argv; Runner sends spec JSON on stdin.
    raise NotImplementedError("stage 3: namespace launch planning")


def build_preflight_plan(spec: ContainerSpec, unshare_path: str) -> LaunchPlan:
    """Return the same namespace setup pointed at a setup-only helper."""
    # TODO(stage 3): validate the same inputs as build_launch_plan, invoke minictr.preflight,
    # and cap this setup-only plan at ten seconds.
    raise NotImplementedError("stage 3: namespace capability preflight planning")
