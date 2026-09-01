from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


@dataclass(frozen=True)
class BackendSettings:
    name: str = "exec"
    command: str = "codex"
    permission_profile: str = "factory-isolated"
    toolchain_read_roots: tuple[str, ...] = ()
    timeout_seconds: float = 1800
    model: str | None = "gpt-5.6-sol"
    reasoning_effort: str | None = "ultra"
    provider: str | None = None
    base_url: str | None = None
    provider_name: str | None = None
    requires_openai_auth: bool = True
    supports_websockets: bool = False


@dataclass(frozen=True)
class FactorySettings:
    root: Path
    database: Path
    warehouse: Path
    config_path: Path | None = None
    lease_seconds: float = 30
    heartbeat_seconds: float = 5
    poll_seconds: float = 0.25
    max_concurrency: int = 3
    allow_host_command_validators: bool = False
    course_revision_limit: int = 2
    shutdown_grace_seconds: float = 10
    limits: dict[str, int] = field(default_factory=dict)
    retry_base_seconds: float = 2
    retry_max_seconds: float = 300
    backend: BackendSettings = field(default_factory=BackendSettings)

    @property
    def migrations(self) -> Path:
        return self.root / "migrations"


def _nonempty(value: Any) -> str | None:
    if value is None:
        return None
    rendered = str(value).strip()
    return rendered or None


def _safe_endpoint(value: Any, *, key: str) -> str | None:
    """Return a persistable HTTP(S) endpoint without credential-bearing parts."""

    rendered = _nonempty(value)
    if rendered is None:
        return None
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in rendered):
        raise ValueError(f"{key} must not contain control characters")
    try:
        parsed = urlsplit(rendered)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise ValueError(f"{key} must be a valid HTTP(S) endpoint") from exc
    if parsed.scheme not in {"http", "https"} or not hostname:
        raise ValueError(f"{key} must be an absolute HTTP(S) endpoint")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{key} must not contain user information")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{key} must not contain a query or fragment")
    return rendered


def _string_tuple(value: Any, *, key: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a TOML array of non-empty strings")
    rendered: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{key} must be a TOML array of non-empty strings")
        rendered.append(item.strip())
    return tuple(rendered)


def load_settings(config_path: Path | None = None) -> FactorySettings:
    root = Path(__file__).resolve().parents[2]
    configured = config_path or Path(os.environ.get("LEARNFACTORY_CONFIG", root / "config/factory.toml"))
    with configured.open("rb") as stream:
        raw = tomllib.load(stream)
    factory = raw.get("factory", {})
    backend = raw.get("backend", {})
    retry = raw.get("retry", {})

    def relative_path(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else root / path

    raw_course_revision_limit = factory.get("course_revision_limit", 2)
    if isinstance(raw_course_revision_limit, bool) or not isinstance(
        raw_course_revision_limit, int
    ):
        raise ValueError("factory.course_revision_limit must be an integer")
    course_revision_limit = raw_course_revision_limit
    if not 0 <= course_revision_limit <= 10:
        raise ValueError("factory.course_revision_limit must be from 0 through 10")

    allow_host_command_validators = factory.get(
        "allow_host_command_validators", False
    )
    if not isinstance(allow_host_command_validators, bool):
        raise ValueError("factory.allow_host_command_validators must be a boolean")

    return FactorySettings(
        root=root,
        database=relative_path(factory.get("database", "warehouse/factory.db")),
        warehouse=relative_path(factory.get("warehouse", "warehouse")),
        config_path=configured.resolve(),
        lease_seconds=float(factory.get("lease_seconds", 30)),
        heartbeat_seconds=float(factory.get("heartbeat_seconds", 5)),
        poll_seconds=float(factory.get("poll_seconds", 0.25)),
        max_concurrency=int(factory.get("max_concurrency", 3)),
        allow_host_command_validators=allow_host_command_validators,
        course_revision_limit=course_revision_limit,
        shutdown_grace_seconds=float(factory.get("shutdown_grace_seconds", 10)),
        limits={str(k): int(v) for k, v in raw.get("limits", {}).items()},
        retry_base_seconds=float(retry.get("base_seconds", 2)),
        retry_max_seconds=float(retry.get("max_seconds", 300)),
        backend=BackendSettings(
            name=str(backend.get("name", "exec")),
            command=str(backend.get("command", "codex")),
            permission_profile=str(
                backend.get("permission_profile", "factory-isolated")
            ),
            toolchain_read_roots=_string_tuple(
                backend.get("toolchain_read_roots"),
                key="backend.toolchain_read_roots",
            ),
            timeout_seconds=float(backend.get("timeout_seconds", 1800)),
            model=_nonempty(backend.get("model", "gpt-5.6-sol")),
            reasoning_effort=_nonempty(backend.get("reasoning_effort", "ultra")),
            provider=_nonempty(backend.get("provider")),
            base_url=_safe_endpoint(backend.get("base_url"), key="backend.base_url"),
            provider_name=_nonempty(backend.get("provider_name")),
            requires_openai_auth=bool(backend.get("requires_openai_auth", True)),
            supports_websockets=bool(backend.get("supports_websockets", False)),
        ),
    )
