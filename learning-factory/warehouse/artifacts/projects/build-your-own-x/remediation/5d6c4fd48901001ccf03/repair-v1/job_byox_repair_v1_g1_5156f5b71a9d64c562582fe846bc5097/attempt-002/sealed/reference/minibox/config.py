"""Strict parsing for Minibox's deliberately small JSON input format."""

from __future__ import annotations

import json
import math
import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .errors import SpecError

_ALLOWED_KEYS = frozenset(
    {
        "schema_version",
        "rootfs",
        "argv",
        "env",
        "hostname",
        "network_mode",
        "timeout_seconds",
    }
)
_REQUIRED_KEYS = frozenset({"schema_version", "rootfs", "argv"})
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z", re.ASCII)
_HOSTNAME = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z", re.ASCII
)
_MAX_SPEC_BYTES = 1_048_576


@dataclass(frozen=True)
class ContainerSpec:
    schema_version: int
    rootfs: Path
    argv: tuple[str, ...]
    env: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({})
    )
    hostname: str = "minibox"
    network_mode: str = "none"
    timeout_seconds: float = 30.0


def _require_plain_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SpecError(f"{name} must be a JSON integer")
    return value


def _check_rootfs(value: Any) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise SpecError("rootfs must be a non-empty path string")
    rootfs = Path(value)
    if not rootfs.is_absolute():
        raise SpecError("rootfs must be absolute")
    if ".." in rootfs.parts:
        raise SpecError("rootfs must not contain '..'")

    current = Path(rootfs.anchor)
    try:
        for part in rootfs.parts[1:]:
            current = current / part
            metadata = os.lstat(current)
            if stat.S_ISLNK(metadata.st_mode):
                raise SpecError("rootfs and its parents must not be symlinks")
    except FileNotFoundError as exc:
        raise SpecError("rootfs does not exist") from exc
    except OSError as exc:
        raise SpecError(f"cannot inspect rootfs: {exc.strerror or exc}") from exc

    try:
        if not stat.S_ISDIR(os.stat(rootfs, follow_symlinks=False).st_mode):
            raise SpecError("rootfs must be a directory")
    except OSError as exc:
        raise SpecError(f"cannot inspect rootfs: {exc.strerror or exc}") from exc
    return rootfs


def from_dict(data: Mapping[str, Any]) -> ContainerSpec:
    if not isinstance(data, Mapping):
        raise SpecError("specification must be a JSON object")
    try:
        normalized = dict(data)
    except (TypeError, ValueError) as exc:
        raise SpecError("specification mapping cannot be read") from exc
    if any(not isinstance(key, str) for key in normalized):
        raise SpecError("specification keys must be strings")
    data = normalized
    keys = frozenset(data)
    unknown = keys - _ALLOWED_KEYS
    missing = _REQUIRED_KEYS - keys
    if unknown:
        raise SpecError(f"unknown specification key: {sorted(unknown)[0]}")
    if missing:
        raise SpecError(f"missing specification key: {sorted(missing)[0]}")

    version = _require_plain_int(data["schema_version"], "schema_version")
    if version != 1:
        raise SpecError("schema_version must be 1")
    rootfs = _check_rootfs(data["rootfs"])

    raw_argv = data["argv"]
    if not isinstance(raw_argv, list) or not raw_argv:
        raise SpecError("argv must be a non-empty JSON array")
    if any(not isinstance(arg, str) for arg in raw_argv):
        raise SpecError("every argv item must be a string")
    if any(not arg for arg in raw_argv):
        raise SpecError("argv items must not be empty")
    if any("\x00" in arg for arg in raw_argv):
        raise SpecError("argv items must not contain NUL")

    raw_env = data.get("env", {})
    if not isinstance(raw_env, Mapping):
        raise SpecError("env must be a JSON object")
    env: dict[str, str] = {}
    for name, value in raw_env.items():
        if not isinstance(name, str) or _ENV_NAME.fullmatch(name) is None:
            raise SpecError("environment names must be POSIX identifiers")
        if not isinstance(value, str) or "\x00" in value:
            raise SpecError(f"environment value for {name!r} must be a NUL-free string")
        env[name] = value

    hostname = data.get("hostname", "minibox")
    if not isinstance(hostname, str) or _HOSTNAME.fullmatch(hostname) is None:
        raise SpecError("hostname must be a lowercase ASCII DNS label of 1..63 characters")

    network_mode = data.get("network_mode", "none")
    if not isinstance(network_mode, str) or network_mode not in {"none", "host"}:
        raise SpecError("network_mode must be 'none' or 'host'")

    raw_timeout = data.get("timeout_seconds", 30.0)
    if isinstance(raw_timeout, bool) or not isinstance(raw_timeout, (int, float)):
        raise SpecError("timeout_seconds must be a JSON number")
    timeout = float(raw_timeout)
    if not math.isfinite(timeout) or timeout <= 0.0 or timeout > 300.0:
        raise SpecError("timeout_seconds must be greater than 0 and at most 300")

    return ContainerSpec(
        schema_version=version,
        rootfs=rootfs,
        argv=tuple(raw_argv),
        env=MappingProxyType(dict(sorted(env.items()))),
        hostname=hostname,
        network_mode=network_mode,
        timeout_seconds=timeout,
    )


def load_spec(path: str | Path) -> ContainerSpec:
    source = Path(path)
    descriptor: int | None = None
    try:
        path_metadata = os.lstat(source)
        if stat.S_ISLNK(path_metadata.st_mode):
            raise SpecError("specification path must be a regular, non-symlink file")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(source, flags)
        metadata = os.fstat(descriptor)
    except SpecError:
        if descriptor is not None:
            os.close(descriptor)
        raise
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
        raise SpecError(f"cannot inspect specification file: {exc.strerror or exc}") from exc
    try:
        if not stat.S_ISREG(metadata.st_mode):
            raise SpecError("specification path must be a regular, non-symlink file")
        if metadata.st_size > _MAX_SPEC_BYTES:
            raise SpecError("specification file is larger than 1 MiB")
        chunks: list[bytes] = []
        remaining = _MAX_SPEC_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        encoded = b"".join(chunks)
        if len(encoded) > _MAX_SPEC_BYTES:
            raise SpecError("specification file is larger than 1 MiB")
        text = encoded.decode("utf-8")

        def reject_constant(value: str) -> None:
            raise ValueError(f"non-finite JSON constant {value!r}")

        def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate JSON key {key!r}")
                result[key] = value
            return result

        decoded = json.loads(
            text,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise SpecError(f"cannot decode specification JSON: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    return from_dict(decoded)
