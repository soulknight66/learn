"""Pure launch-plan construction; this module starts no processes."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat
import sys
from typing import Mapping

from .errors import ValidationError
from .paths import resolve_guest_path, validate_rootfs
from .spec import ContainerSpec

PREFLIGHT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class LaunchPlan:
    argv: tuple[str, ...]
    helper_env_items: tuple[tuple[str, str], ...]
    timeout_seconds: float

    @property
    def helper_env(self) -> Mapping[str, str]:
        return dict(self.helper_env_items)


def _validate_executable(path_text: str) -> Path:
    if not isinstance(path_text, str) or "\0" in path_text:
        raise ValidationError("unshare_path must be an absolute executable path")
    path = Path(path_text)
    if not path.is_absolute() or path.is_symlink():
        raise ValidationError("unshare_path must be an absolute nonsymlink path")
    try:
        mode = path.stat().st_mode
    except OSError as exc:
        raise ValidationError("unshare executable is unavailable") from exc
    if not stat.S_ISREG(mode) or not os.access(path, os.X_OK):
        raise ValidationError("unshare_path must name an executable regular file")
    return path


def _build_helper_plan(
    spec: ContainerSpec,
    unshare_path: str,
    module: str,
    timeout_seconds: float,
) -> LaunchPlan:
    if not isinstance(spec, ContainerSpec):
        raise ValidationError("spec must be a ContainerSpec")
    unshare = _validate_executable(unshare_path)
    root = validate_rootfs(spec.rootfs)
    proc_mount = root / "proc"
    if proc_mount.is_symlink() or not proc_mount.is_dir():
        raise ValidationError("rootfs must contain a real proc directory")
    resolve_guest_path(root, "/proc")
    package_root = Path(__file__).resolve().parents[1]
    flags = [
        str(unshare),
        "--user",
        "--map-root-user",
        "--mount",
        "--uts",
        "--ipc",
        "--pid",
        "--fork",
        "--kill-child=SIGKILL",
    ]
    if not spec.network:
        flags.append("--net")
    flags.extend(
        [
            "--",
            sys.executable,
            "-m",
            module,
        ]
    )
    helper_env = tuple(
        sorted(
            {
                "LANG": "C",
                "LC_ALL": "C",
                "PATH": "/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(package_root),
            }.items()
        )
    )
    return LaunchPlan(tuple(flags), helper_env, timeout_seconds)


def build_launch_plan(spec: ContainerSpec, unshare_path: str) -> LaunchPlan:
    """Build the workload helper plan without starting a process."""
    return _build_helper_plan(spec, unshare_path, "minictr.child", spec.timeout_seconds)


def build_preflight_plan(spec: ContainerSpec, unshare_path: str) -> LaunchPlan:
    """Build a bounded setup-only plan used before opting into workload execution."""
    return _build_helper_plan(
        spec,
        unshare_path,
        "minictr.preflight",
        min(spec.timeout_seconds, PREFLIGHT_TIMEOUT_SECONDS),
    )
