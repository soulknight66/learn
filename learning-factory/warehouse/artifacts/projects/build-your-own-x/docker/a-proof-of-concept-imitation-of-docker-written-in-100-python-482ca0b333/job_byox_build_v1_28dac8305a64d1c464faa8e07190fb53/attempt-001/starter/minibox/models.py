"""Immutable public models and validation rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence

from .errors import InvalidIdentifier, InvalidSpec, InvalidTransition


class ContainerState(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    EXITED = "EXITED"
    FAILED = "FAILED"
    DELETED = "DELETED"


def validate_identifier(value: object) -> str:
    """Return a valid canonical identifier or raise InvalidIdentifier."""
    raise NotImplementedError("milestone 1: validate identifiers")


def validate_transition(current: ContainerState, target: ContainerState) -> None:
    """Raise InvalidTransition unless current -> target is an allowed edge."""
    raise NotImplementedError("milestone 1: validate the lifecycle graph")


@dataclass(frozen=True)
class ContainerSpec:
    container_id: str
    image_id: str
    argv: tuple[str, ...]
    env: Mapping[str, str] = field(default_factory=dict)
    working_dir: str = "/"
    network: bool = False

    def __post_init__(self) -> None:
        raise NotImplementedError("milestone 1: validate and freeze container specs")

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
