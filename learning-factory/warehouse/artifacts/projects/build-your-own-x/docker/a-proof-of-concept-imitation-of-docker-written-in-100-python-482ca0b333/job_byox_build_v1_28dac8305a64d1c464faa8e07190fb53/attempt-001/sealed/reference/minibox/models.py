"""Immutable public models and validation rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
import re
from types import MappingProxyType
from typing import Mapping, Sequence

from .errors import InvalidIdentifier, InvalidSpec, InvalidTransition


_IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}", re.ASCII)
_ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*", re.ASCII)


class ContainerState(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    EXITED = "EXITED"
    FAILED = "FAILED"
    DELETED = "DELETED"


_TRANSITIONS: dict[ContainerState, frozenset[ContainerState]] = {
    ContainerState.CREATED: frozenset((ContainerState.RUNNING, ContainerState.DELETED)),
    ContainerState.RUNNING: frozenset((ContainerState.EXITED, ContainerState.FAILED)),
    ContainerState.EXITED: frozenset((ContainerState.RUNNING, ContainerState.DELETED)),
    ContainerState.FAILED: frozenset((ContainerState.RUNNING, ContainerState.DELETED)),
    ContainerState.DELETED: frozenset(),
}


def validate_identifier(value: object) -> str:
    """Return a valid canonical identifier or raise InvalidIdentifier."""
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise InvalidIdentifier(
            "identifier must be 1-64 lowercase ASCII letters, digits, '.', '_' or '-' "
            "and start with a letter or digit"
        )
    return value


def validate_transition(current: ContainerState, target: ContainerState) -> None:
    """Raise InvalidTransition unless current -> target is an allowed edge."""
    if not isinstance(current, ContainerState) or not isinstance(target, ContainerState):
        raise InvalidTransition("states must be ContainerState values")
    if target not in _TRANSITIONS[current]:
        raise InvalidTransition(f"transition {current.value} -> {target.value} is not allowed")


@dataclass(frozen=True)
class ContainerSpec:
    container_id: str
    image_id: str
    argv: tuple[str, ...]
    env: Mapping[str, str] = field(default_factory=dict)
    working_dir: str = "/"
    network: bool = False

    def __post_init__(self) -> None:
        validate_identifier(self.container_id)
        validate_identifier(self.image_id)

        if isinstance(self.argv, (str, bytes)):
            raise InvalidSpec("argv must be a non-empty sequence of strings")
        try:
            frozen_argv = tuple(self.argv)
        except TypeError as exc:
            raise InvalidSpec("argv must be a non-empty sequence of strings") from exc
        if not frozen_argv:
            raise InvalidSpec("argv must not be empty")
        if any(not isinstance(item, str) or not item or "\x00" in item for item in frozen_argv):
            raise InvalidSpec("every argv item must be a non-empty NUL-free string")

        if not isinstance(self.env, Mapping):
            raise InvalidSpec("env must be a mapping")
        frozen_env: dict[str, str] = {}
        for name, value in self.env.items():
            if not isinstance(name, str) or _ENVIRONMENT_NAME.fullmatch(name) is None:
                raise InvalidSpec(f"invalid environment variable name: {name!r}")
            if not isinstance(value, str) or "\x00" in value:
                raise InvalidSpec(f"environment value for {name!r} must be a NUL-free string")
            frozen_env[name] = value

        if not isinstance(self.working_dir, str) or "\x00" in self.working_dir:
            raise InvalidSpec("working_dir must be a NUL-free string")
        path = PurePosixPath(self.working_dir)
        if (
            not path.is_absolute()
            or self.working_dir.startswith("//")
            or ".." in path.parts
            or str(path) != self.working_dir
        ):
            raise InvalidSpec("working_dir must be a normalized absolute POSIX path without '..'")
        if type(self.network) is not bool:
            raise InvalidSpec("network must be a boolean")

        object.__setattr__(self, "argv", frozen_argv)
        object.__setattr__(self, "env", MappingProxyType(dict(sorted(frozen_env.items()))))

    def to_dict(self) -> dict[str, object]:
        return {
            "argv": list(self.argv),
            "container_id": self.container_id,
            "env": dict(self.env),
            "image_id": self.image_id,
            "network": self.network,
            "working_dir": self.working_dir,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ContainerSpec":
        if not isinstance(value, Mapping):
            raise InvalidSpec("serialized spec must be a mapping")
        try:
            argv_value = value["argv"]
            if isinstance(argv_value, (str, bytes)) or not isinstance(argv_value, Sequence):
                raise TypeError("argv must be a sequence")
            env_value = value.get("env", {})
            if not isinstance(env_value, Mapping):
                raise TypeError("env must be a mapping")
            return cls(
                container_id=value["container_id"],  # type: ignore[arg-type]
                image_id=value["image_id"],  # type: ignore[arg-type]
                argv=tuple(argv_value),
                env=dict(env_value),
                working_dir=value.get("working_dir", "/"),  # type: ignore[arg-type]
                network=value.get("network", False),  # type: ignore[arg-type]
            )
        except (KeyError, TypeError) as exc:
            raise InvalidSpec(f"invalid serialized spec: {exc}") from exc
