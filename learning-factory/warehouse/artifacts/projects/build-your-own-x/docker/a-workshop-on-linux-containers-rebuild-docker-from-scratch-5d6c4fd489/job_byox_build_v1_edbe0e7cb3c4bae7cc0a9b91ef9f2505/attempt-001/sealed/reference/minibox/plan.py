"""Pure construction of the namespace launcher argument vector."""

from __future__ import annotations

from dataclasses import dataclass
from .config import ContainerSpec
from .errors import BackendUnavailable


@dataclass(frozen=True)
class IsolationPlan:
    namespaces: tuple[str, ...]
    argv: tuple[str, ...]


def _program_token(value: str, name: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise BackendUnavailable(f"{name} must be a non-empty path")
    return value


def build_plan(
    spec: ContainerSpec,
    *,
    unshare_path: str = "/usr/bin/unshare",
    python_path: str = "/usr/bin/python3",
) -> IsolationPlan:
    unshare = _program_token(unshare_path, "unshare_path")
    python = _program_token(python_path, "python_path")

    namespaces = ["user", "mount", "pid", "uts", "ipc"]
    argv = [
        unshare,
        "--user",
        "--map-root-user",
        "--mount",
        "--pid",
        "--fork",
        "--uts",
        "--ipc",
    ]
    if spec.network_mode == "none":
        namespaces.append("net")
        argv.append("--net")
    argv.extend(["--", python, "-m", "minibox._child"])
    return IsolationPlan(tuple(namespaces), tuple(argv))
