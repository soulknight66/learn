"""SQLite-backed container lifecycle state."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
import time
from typing import Callable

from .errors import (
    ContainerExists,
    ContainerNotFound,
    InvalidTransition,
    StateConflict,
    StateCorruption,
)
from .models import ContainerSpec, ContainerState, validate_identifier, validate_transition


_MIGRATION_NAME = re.compile(r"([0-9]{3})_[a-z0-9_]+\.sql")


@dataclass(frozen=True)
class ContainerRecord:
    container_id: str
    spec: ContainerSpec
    state: ContainerState
    exit_code: int | None
    created_ns: int
    updated_ns: int


@dataclass(frozen=True)
class StateEvent:
    sequence: int
    container_id: str
    from_state: ContainerState | None
    to_state: ContainerState
    exit_code: int | None
    at_ns: int


class StateStore:
    def __init__(
        self,
        database: str | Path,
        *,
        migrations: str | Path | None = None,
        clock_ns: Callable[[], int] | None = None,
    ) -> None:
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.migrations = (
            Path(migrations)
            if migrations is not None
            else Path(__file__).resolve().parent.parent / "migrations"
        )
        self._clock_ns = clock_ns if clock_ns is not None else time.time_ns
        self._apply_migrations()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=5.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _apply_migrations(self) -> None:
        if not self.migrations.is_dir():
            raise StateCorruption(f"migration directory is unavailable: {self.migrations}")
        numbered: list[tuple[int, Path]] = []
        for path in sorted(self.migrations.iterdir()):
            if not path.is_file():
                continue
            match = _MIGRATION_NAME.fullmatch(path.name)
            if match is None:
                raise StateCorruption(f"invalid migration filename: {path.name}")
            numbered.append((int(match.group(1)), path))
        expected = list(range(1, len(numbered) + 1))
        if [number for number, _ in numbered] != expected:
            raise StateCorruption("migrations must be consecutively numbered from 001")

        connection = self._connect()
        try:
            current = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if current > len(numbered):
                raise StateCorruption(f"database schema version {current} is newer than this program")
            for number, path in numbered:
                if number <= current:
                    continue
                script = path.read_text(encoding="utf-8")
                try:
                    connection.executescript(script)
                except sqlite3.DatabaseError as exc:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                    raise StateCorruption(f"migration {path.name} failed: {exc}") from exc
                applied = int(connection.execute("PRAGMA user_version").fetchone()[0])
                if applied != number:
                    raise StateCorruption(
                        f"migration {path.name} set schema version {applied}, expected {number}"
                    )
        finally:
            connection.close()

    def _now(self) -> int:
        value = self._clock_ns()
        if type(value) is not int or value < 0:
            raise StateCorruption("clock must return a non-negative integer nanosecond value")
        return value

    @staticmethod
    def _record(row: sqlite3.Row) -> ContainerRecord:
        try:
            raw_spec = json.loads(row["spec_json"])
            return ContainerRecord(
                container_id=row["container_id"],
                spec=ContainerSpec.from_dict(raw_spec),
                state=ContainerState(row["state"]),
                exit_code=row["exit_code"],
                created_ns=row["created_ns"],
                updated_ns=row["updated_ns"],
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise StateCorruption("invalid container record in database") from exc

    @staticmethod
    def _select_record(connection: sqlite3.Connection, container_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT container_id, spec_json, state, exit_code, created_ns, updated_ns "
            "FROM containers WHERE container_id = ?",
            (container_id,),
        ).fetchone()
        if row is None:
            raise ContainerNotFound(f"container does not exist: {container_id}")
        return row

    def create(self, spec: ContainerSpec) -> ContainerRecord:
        if not isinstance(spec, ContainerSpec):
            raise TypeError("spec must be a ContainerSpec")
        now = self._now()
        spec_json = json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":"))
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "INSERT INTO containers "
                    "(container_id, spec_json, state, exit_code, created_ns, updated_ns) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (spec.container_id, spec_json, ContainerState.CREATED.value, None, now, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ContainerExists(f"container already exists: {spec.container_id}") from exc
            connection.execute(
                "INSERT INTO state_events "
                "(container_id, from_state, to_state, exit_code, at_ns) VALUES (?, ?, ?, ?, ?)",
                (spec.container_id, None, ContainerState.CREATED.value, None, now),
            )
            row = self._select_record(connection, spec.container_id)
            connection.execute("COMMIT")
            return self._record(row)
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def get(self, container_id: str) -> ContainerRecord:
        canonical_id = validate_identifier(container_id)
        connection = self._connect()
        try:
            return self._record(self._select_record(connection, canonical_id))
        finally:
            connection.close()

    def transition(
        self,
        container_id: str,
        expected: ContainerState,
        target: ContainerState,
        *,
        exit_code: int | None = None,
    ) -> ContainerRecord:
        canonical_id = validate_identifier(container_id)
        validate_transition(expected, target)
        if target is ContainerState.EXITED:
            if type(exit_code) is not int:
                raise InvalidTransition("EXITED requires an integer exit code")
        elif exit_code is not None:
            raise InvalidTransition("only EXITED may carry an exit code")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._select_record(connection, canonical_id)
            durable_state = ContainerState(row["state"])
            if durable_state is not expected:
                raise StateConflict(
                    f"expected {expected.value} for {canonical_id}, found {durable_state.value}"
                )
            now = max(self._now(), int(row["updated_ns"]) + 1)
            try:
                connection.execute(
                    "UPDATE containers SET state = ?, exit_code = ?, updated_ns = ? "
                    "WHERE container_id = ?",
                    (target.value, exit_code, now, canonical_id),
                )
            except sqlite3.IntegrityError as exc:
                raise InvalidTransition(
                    f"database rejected transition {expected.value} -> {target.value}"
                ) from exc
            updated = self._select_record(connection, canonical_id)
            connection.execute("COMMIT")
            return self._record(updated)
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def events(self, container_id: str) -> list[StateEvent]:
        canonical_id = validate_identifier(container_id)
        connection = self._connect()
        try:
            self._select_record(connection, canonical_id)
            rows = connection.execute(
                "SELECT sequence, container_id, from_state, to_state, exit_code, at_ns "
                "FROM state_events WHERE container_id = ? ORDER BY sequence",
                (canonical_id,),
            ).fetchall()
        finally:
            connection.close()
        try:
            return [
                StateEvent(
                    sequence=row["sequence"],
                    container_id=row["container_id"],
                    from_state=(
                        ContainerState(row["from_state"]) if row["from_state"] is not None else None
                    ),
                    to_state=ContainerState(row["to_state"]),
                    exit_code=row["exit_code"],
                    at_ns=row["at_ns"],
                )
                for row in rows
            ]
        except ValueError as exc:
            raise StateCorruption("invalid event record in database") from exc
