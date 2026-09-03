"""SQLite-backed lifecycle state with database-enforced transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3

from .errors import TransitionError, ValidationError
from .spec import ContainerSpec

_CREATE_CONTAINERS = """
CREATE TABLE IF NOT EXISTS containers (
    id TEXT PRIMARY KEY,
    state TEXT NOT NULL CHECK (state IN ('CREATED', 'RUNNING', 'EXITED', 'FAILED')),
    pid INTEGER,
    exit_code INTEGER,
    spec_json TEXT NOT NULL,
    log_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (pid IS NULL OR pid > 0)
)
"""
_MIGRATIONS = (
    (1, Path(__file__).with_name("migrations") / "001_fixed_transition_policy.sql"),
)

_RFC3339_TIMESTAMP = re.compile(
    r"[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])"
    r"[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]+)?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)


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


def _validate_timestamp(value: str) -> str:
    if not isinstance(value, str) or _RFC3339_TIMESTAMP.fullmatch(value) is None:
        raise ValidationError("timestamp must be an RFC 3339 string")
    normalized = value[:10] + "T" + value[11:]
    if normalized.endswith(("Z", "z")):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValidationError("timestamp must be RFC 3339") from exc
    if parsed.tzinfo is None:
        raise ValidationError("timestamp must include a timezone")
    return value


def _migration_statements(path: Path) -> tuple[str, ...]:
    """Read one numbered migration without giving sqlite3 an implicit transaction."""
    statements: list[str] = []
    pending = ""
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            statements.append(pending.strip())
            pending = ""
    if pending.strip():
        raise sqlite3.DatabaseError(f"incomplete migration: {path.name}")
    if not statements:
        raise sqlite3.DatabaseError(f"empty migration: {path.name}")
    return tuple(statements)


def _record(row: sqlite3.Row) -> ContainerRecord:
    return ContainerRecord(
        row["id"], row["state"], row["pid"], row["exit_code"], row["spec_json"],
        row["log_path"], row["created_at"], row["updated_at"],
    )


class Registry:
    def __init__(self, path: Path):
        if not isinstance(path, Path):
            raise ValidationError("registry path must be a Path")
        self.path = path
        self.connection = sqlite3.connect(path, isolation_level=None, timeout=5.0)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    def _initialize(self) -> None:
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.execute(_CREATE_CONTAINERS)
            row = self.connection.execute("PRAGMA user_version").fetchone()
            version = int(row[0])
            latest = _MIGRATIONS[-1][0]
            if version < 0 or version > latest:
                raise sqlite3.DatabaseError(f"unsupported registry schema version: {version}")
            for target, migration_path in _MIGRATIONS:
                if target <= version:
                    continue
                for statement in _migration_statements(migration_path):
                    self.connection.execute(statement)
                self.connection.execute(f"PRAGMA user_version = {target}")
                version = target
            self.connection.commit()
        except (OSError, UnicodeError, sqlite3.Error):
            if self.connection.in_transaction:
                self.connection.rollback()
            self.connection.close()
            raise

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Registry":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _transaction(self, statement: str, parameters: tuple[object, ...]) -> ContainerRecord:
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            cursor = self.connection.execute(statement, parameters)
            if cursor.rowcount != 1:
                raise TransitionError("lifecycle transition was not available")
            row = self.connection.execute(
                "SELECT id, state, pid, exit_code, spec_json, log_path, created_at, updated_at "
                "FROM containers WHERE id = ?",
                (parameters[-1],),
            ).fetchone()
            if row is None:
                raise TransitionError("container disappeared during transaction")
            self.connection.commit()
            return _record(row)
        except (sqlite3.Error, TransitionError) as exc:
            if self.connection.in_transaction:
                self.connection.rollback()
            if isinstance(exc, TransitionError):
                raise
            raise TransitionError(str(exc)) from exc

    def create(self, spec: ContainerSpec, now: str) -> ContainerRecord:
        if not isinstance(spec, ContainerSpec):
            raise ValidationError("spec must be a ContainerSpec")
        now = _validate_timestamp(now)
        spec_json = json.dumps(spec.to_mapping(), sort_keys=True, separators=(",", ":"))
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            self.connection.execute(
                "INSERT INTO containers(id, state, pid, exit_code, spec_json, log_path, created_at, updated_at) "
                "VALUES (?, 'CREATED', NULL, NULL, ?, NULL, ?, ?)",
                (spec.container_id, spec_json, now, now),
            )
            row = self.connection.execute(
                "SELECT id, state, pid, exit_code, spec_json, log_path, created_at, updated_at "
                "FROM containers WHERE id = ?",
                (spec.container_id,),
            ).fetchone()
            self.connection.commit()
            if row is None:
                raise TransitionError("created container could not be read back")
            return _record(row)
        except (sqlite3.Error, TransitionError) as exc:
            if self.connection.in_transaction:
                self.connection.rollback()
            if isinstance(exc, TransitionError):
                raise
            raise TransitionError(str(exc)) from exc

    def claim_start(self, container_id: str, pid: int, now: str) -> ContainerRecord:
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
            raise ValidationError("pid must be a positive integer")
        now = _validate_timestamp(now)
        return self._transaction(
            "UPDATE containers SET state = 'RUNNING', pid = ?, updated_at = ? "
            "WHERE id = ? AND state = 'CREATED'",
            (pid, now, container_id),
        )

    def finish(self, container_id: str, exit_code: int, log_path: str, now: str) -> ContainerRecord:
        if isinstance(exit_code, bool) or not isinstance(exit_code, int) or not -(2**31) <= exit_code < 2**31:
            raise ValidationError("exit_code must be a signed 32-bit integer")
        if not isinstance(log_path, str) or not log_path or "\0" in log_path:
            raise ValidationError("log_path must be a nonempty string without NUL")
        now = _validate_timestamp(now)
        state = "EXITED" if exit_code == 0 else "FAILED"
        return self._transaction(
            "UPDATE containers SET state = ?, exit_code = ?, log_path = ?, updated_at = ? "
            "WHERE id = ? AND state = 'RUNNING'",
            (state, exit_code, log_path, now, container_id),
        )

    def get(self, container_id: str) -> ContainerRecord:
        row = self.connection.execute(
            "SELECT id, state, pid, exit_code, spec_json, log_path, created_at, updated_at "
            "FROM containers WHERE id = ?",
            (container_id,),
        ).fetchone()
        if row is None:
            raise TransitionError(f"unknown container: {container_id}")
        return _record(row)
