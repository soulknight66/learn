"""Validated domain values consumed by the pure policy."""

from enum import Enum
from typing import Dict, NamedTuple, Union


class Role(str, Enum):
    MEMBER = "member"
    AUDITOR = "auditor"
    ADMIN = "admin"


class Action(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"


class Principal(NamedTuple):
    subject_id: str
    tenant_id: str
    role: Role


class Resource(NamedTuple):
    resource_id: str
    tenant_id: str
    owner_id: str


class AuthorizationRequest(NamedTuple):
    principal: Principal
    action: Action
    resource: Resource


class Decision(NamedTuple):
    allowed: bool
    reason: str

    def as_dict(self) -> Dict[str, Union[bool, str]]:
        return {"allowed": self.allowed, "reason": self.reason}
