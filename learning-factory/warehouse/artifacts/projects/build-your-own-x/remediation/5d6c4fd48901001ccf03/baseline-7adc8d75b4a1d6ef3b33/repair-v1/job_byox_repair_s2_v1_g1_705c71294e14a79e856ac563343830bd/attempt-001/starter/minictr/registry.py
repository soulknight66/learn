"""Durable lifecycle registry skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from .errors import TransitionError
from .spec import ContainerSpec


@dataclass(frozen=True, slots=True)
class ContainerRecord:
    container_id: str
    state: str
    pid: int | None
    exit_code: int | None
    spec_json: str
    log_path: str | None
    created_at: str
    updated_at: str


class Registry:
    def __init__(self, path: Path):
        self.path = path
        self.connection = sqlite3.connect(path, isolation_level=None, timeout=5.0)
        self.connection.row_factory = sqlite3.Row
        # TODO(stage 4): create constrained tables, allowed transitions, and a transition trigger.

    def close(self) -> None:
        self.connection.close()

    def create(self, spec: ContainerSpec, now: str) -> ContainerRecord:
        raise NotImplementedError("stage 4: transactional create")

    def claim_start(self, container_id: str, pid: int, now: str) -> ContainerRecord:
        raise NotImplementedError("stage 4: BEGIN IMMEDIATE atomic claim")

    def finish(self, container_id: str, exit_code: int, log_path: str, now: str) -> ContainerRecord:
        raise NotImplementedError("stage 4: durable terminal transition")

    def get(self, container_id: str) -> ContainerRecord:
        row = self.connection.execute(
            "SELECT id, state, pid, exit_code, spec_json, log_path, created_at, updated_at "
            "FROM containers WHERE id = ?",
            (container_id,),
        ).fetchone()
        if row is None:
            raise TransitionError(f"unknown container: {container_id}")
        return ContainerRecord(row["id"], row["state"], row["pid"], row["exit_code"], row["spec_json"], row["log_path"], row["created_at"], row["updated_at"])
