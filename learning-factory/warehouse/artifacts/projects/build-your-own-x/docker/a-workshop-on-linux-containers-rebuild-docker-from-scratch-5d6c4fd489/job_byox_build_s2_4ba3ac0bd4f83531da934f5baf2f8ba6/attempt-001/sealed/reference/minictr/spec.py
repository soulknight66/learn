"""Strict immutable container specification."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping

from .errors import ValidationError

_ID = re.compile(r"[a-z][a-z0-9_-]{0,31}\Z")
_HOSTNAME = re.compile(r"[a-z0-9.-]{1,63}\Z")
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_FIELDS = frozenset(
    {"id", "rootfs", "command", "hostname", "env", "timeout_seconds", "readonly_root", "network"}
)


@dataclass(frozen=True, slots=True)
class ContainerSpec:
    container_id: str
    rootfs: Path
    command: tuple[str, ...]
    hostname: str
    env_items: tuple[tuple[str, str], ...]
    timeout_seconds: float
    readonly_root: bool
    network: bool

    @property
    def env(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self.env_items))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ContainerSpec":
        if not isinstance(value, Mapping):
            raise ValidationError("spec must be a mapping")
        unknown = set(value) - _FIELDS
        if unknown:
            raise ValidationError(f"unknown fields: {', '.join(sorted(map(str, unknown)))}")
        container_id = value.get("id")
        if not isinstance(container_id, str) or _ID.fullmatch(container_id) is None:
            raise ValidationError("id must match [a-z][a-z0-9_-]{0,31}")

        root_text = value.get("rootfs")
        if not isinstance(root_text, str) or "\0" in root_text:
            raise ValidationError("rootfs must be an absolute path string")
        rootfs = Path(root_text)
        if not rootfs.is_absolute():
            raise ValidationError("rootfs must be absolute")

        command_value = value.get("command")
        if (
            not isinstance(command_value, list)
            or not command_value
            or any(not isinstance(arg, str) or not arg or "\0" in arg for arg in command_value)
        ):
            raise ValidationError("command must be a nonempty list of nonempty strings without NUL")

        hostname = value.get("hostname", container_id)
        if not isinstance(hostname, str) or _HOSTNAME.fullmatch(hostname) is None:
            raise ValidationError("hostname must contain 1-63 lower-case letters, digits, dots, or hyphens")

        env_value = value.get("env", {})
        if not isinstance(env_value, Mapping) or len(env_value) > 128:
            raise ValidationError("env must be a mapping with at most 128 entries")
        env_items: list[tuple[str, str]] = []
        for key, item in env_value.items():
            if not isinstance(key, str) or _ENV_NAME.fullmatch(key) is None:
                raise ValidationError("invalid environment variable name")
            if not isinstance(item, str) or "\0" in item:
                raise ValidationError("environment values must be strings without NUL")
            env_items.append((key, item))

        timeout = value.get("timeout_seconds", 30.0)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValidationError("timeout_seconds must be numeric")
        timeout = float(timeout)
        if not math.isfinite(timeout) or not 0.1 <= timeout <= 300.0:
            raise ValidationError("timeout_seconds must be finite and between 0.1 and 300")

        readonly_root = value.get("readonly_root", True)
        network = value.get("network", False)
        if type(readonly_root) is not bool or type(network) is not bool:
            raise ValidationError("readonly_root and network must be booleans")
        return cls(
            container_id,
            rootfs,
            tuple(command_value),
            hostname,
            tuple(sorted(env_items)),
            timeout,
            readonly_root,
            network,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "id": self.container_id,
            "rootfs": str(self.rootfs),
            "command": list(self.command),
            "hostname": self.hostname,
            "env": dict(self.env_items),
            "timeout_seconds": self.timeout_seconds,
            "readonly_root": self.readonly_root,
            "network": self.network,
        }
