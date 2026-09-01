from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .util import canonical_json, now


class MigrationError(RuntimeError):
    pass


class ClosingConnection(sqlite3.Connection):
    """Preserve sqlite transaction context semantics and close deterministically on exit."""

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        try:
            return bool(super().__exit__(exc_type, exc_value, traceback))
        finally:
            self.close()


def _sql_statements(script: str) -> Iterator[str]:
    """Split a migration with SQLite's own completeness parser.

    ``Connection.executescript`` commits before executing, so it cannot keep the
    version check and DDL under one lock. This line accumulator handles triggers
    and comments while preserving an explicit transaction.
    """

    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            if pending.strip():
                yield pending
            pending = ""
    if pending.strip():
        raise MigrationError("migration ends with an incomplete SQL statement")


class Database:
    """Small connection factory tuned for SQLite 3.26 on an NFS workspace."""

    def __init__(self, path: Path, migrations: Path):
        self.path = path
        self.migrations = migrations

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.path,
            timeout=30,
            isolation_level=None,
            check_same_thread=False,
            factory=ClosingConnection,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA journal_mode = DELETE")
        return connection

    def migrate(self) -> list[str]:
        applied: list[str] = []
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    checksum TEXT NOT NULL,
                    applied_at REAL NOT NULL
                )
                """
            )
            for migration in sorted(self.migrations.glob("[0-9][0-9][0-9]_*.sql")):
                content = migration.read_text(encoding="utf-8")
                checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
                try:
                    # The version check belongs behind the same write lock as the
                    # migration. Reading all versions before acquiring the lock lets
                    # concurrent starters both attempt the same DDL.
                    connection.execute("BEGIN IMMEDIATE")
                    existing = connection.execute(
                        "SELECT checksum FROM schema_migrations WHERE version=?",
                        (migration.name,),
                    ).fetchone()
                    if existing is not None:
                        if existing["checksum"] != checksum:
                            raise MigrationError(f"applied migration changed: {migration.name}")
                        connection.commit()
                        continue
                    for statement in _sql_statements(content):
                        connection.execute(statement)
                    connection.execute(
                        "INSERT INTO schema_migrations(version,checksum,applied_at) VALUES (?,?,?)",
                        (migration.name, checksum, now()),
                    )
                    connection.commit()
                except MigrationError:
                    if connection.in_transaction:
                        connection.rollback()
                    raise
                except sqlite3.Error as error:
                    if connection.in_transaction:
                        connection.rollback()
                    raise MigrationError(f"migration {migration.name} failed: {error}") from error
                applied.append(migration.name)
        return applied

    @contextlib.contextmanager
    def transaction(self, *, immediate: bool = False) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            yield connection
            connection.commit()
        except BaseException:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def emit_event(
        self,
        actor: str,
        event_type: str,
        *,
        job_id: str | None = None,
        worker_id: str | None = None,
        payload: dict[str, Any] | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        values = (now(), actor, job_id, worker_id, event_type, canonical_json(payload or {}))
        if connection is not None:
            connection.execute(
                "INSERT INTO events(timestamp,actor,job_id,worker_id,type,payload_json) VALUES (?,?,?,?,?,?)",
                values,
            )
            return
        with self.transaction(immediate=True) as owned:
            owned.execute(
                "INSERT INTO events(timestamp,actor,job_id,worker_id,type,payload_json) VALUES (?,?,?,?,?,?)",
                values,
            )

    def get_system_value(self, key: str, default: Any = None) -> Any:
        with self.connect() as connection:
            row = connection.execute("SELECT value_json FROM system_state WHERE key=?", (key,)).fetchone()
        if row is None:
            return default
        return json.loads(row["value_json"])

    def set_system_value(self, key: str, value: Any) -> None:
        with self.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO system_state(key,value_json,updated_at) VALUES (?,?,?)
                ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at
                """,
                (key, canonical_json(value), now()),
            )
