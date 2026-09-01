from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sqlite3
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .util import canonical_json, now


class MigrationError(RuntimeError):
    pass


class AuthorizerGuardError(RuntimeError):
    """An ordinary caller tried to replace a guarded SQLite authorizer."""


class _AuthorizerGuardCapability:
    """Unforgeable-by-API identity used by publication internals."""

    __slots__ = ()


@dataclass(frozen=True)
class _Migration:
    path: Path
    version: str
    content: str
    checksum: str


class ClosingConnection(sqlite3.Connection):
    """Close deterministically and track authorizers installed through this API.

    Python 3.11's SQLite binding can install but cannot inspect an authorizer.
    Publication therefore refuses a tracked pre-existing callback, temporarily
    guards a fresh controller connection, and restores its original ``None``
    authorizer after the restricted callback returns.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.__authorizer_lock = threading.RLock()
        self.__learnfactory_authorizer: object | None = None
        self.__authorizer_guard: _AuthorizerGuardCapability | None = None
        self.__guarded_authorizer: object | None = None
        self.__guarded_previous_authorizer: object | None = None
        self.__authorizer_guard_violation_reason: str | None = None

    def set_authorizer(self, authorizer_callback: object | None) -> None:
        with self.__authorizer_lock:
            if self.__authorizer_guard is None:
                sqlite3.Connection.set_authorizer(  # type: ignore[arg-type]
                    self,
                    authorizer_callback,
                )
                self.__learnfactory_authorizer = authorizer_callback
                return
            reason = (
                "publication database authorizer replacement is forbidden "
                "while the capability is active"
            )
            if self.__authorizer_guard_violation_reason is None:
                self.__authorizer_guard_violation_reason = reason
        # Recording is synchronous under the connection lock, but policy code
        # is deliberately not called here. Publication code may hold its policy
        # RLock while a helper thread attempts this mutation. Calling back into
        # policy on that helper would deadlock. The next reassertion or guarded
        # restoration returns this sticky reason to policy instead.
        raise AuthorizerGuardError(reason)

    @property
    def learnfactory_authorizer(self) -> object | None:
        with self.__authorizer_lock:
            return self.__learnfactory_authorizer

    def _begin_authorizer_guard(
        self,
        authorizer_callback: object,
    ) -> tuple[_AuthorizerGuardCapability, object | None]:
        """Install a guarded authorizer and return its opaque capability."""

        with self.__authorizer_lock:
            if self.__authorizer_guard is not None:
                raise AuthorizerGuardError(
                    "database authorizer is already guarded"
                )
            previous = self.__learnfactory_authorizer
            # An authorizer is arbitrary reentrant Python. If it closes over
            # this raw connection, it can replace the guarded callback and run
            # nested SQL before a composing policy regains control. There is no
            # sound in-process way to compose it, so publication refuses the
            # connection atomically and leaves the callback untouched.
            if previous is not None:
                raise AuthorizerGuardError(
                    "publication requires a connection without a pre-existing "
                    "database authorizer"
                )
            capability = _AuthorizerGuardCapability()
            self.__authorizer_guard = capability
            self.__guarded_authorizer = authorizer_callback
            self.__guarded_previous_authorizer = previous
            self.__authorizer_guard_violation_reason = None
            try:
                sqlite3.Connection.set_authorizer(  # type: ignore[arg-type]
                    self,
                    authorizer_callback,
                )
            except BaseException:
                self.__authorizer_guard = None
                self.__guarded_authorizer = None
                self.__guarded_previous_authorizer = None
                self.__authorizer_guard_violation_reason = None
                raise
            self.__learnfactory_authorizer = authorizer_callback
            return capability, previous

    def _reassert_authorizer_guard(
        self,
        capability: _AuthorizerGuardCapability,
    ) -> str | None:
        """Unconditionally reinstall the guarded callback.

        Calling the base descriptor is intentional. Trusted controller code can
        invoke that descriptor directly and thereby bypass this subclass's
        tracking. Reinstallation is the only available repair primitive on
        Python versions where sqlite3 cannot inspect the current callback.
        """

        with self.__authorizer_lock:
            if (
                capability is not self.__authorizer_guard
                or self.__guarded_authorizer is None
            ):
                raise AuthorizerGuardError(
                    "invalid database authorizer guard capability"
                )
            sqlite3.Connection.set_authorizer(  # type: ignore[arg-type]
                self,
                self.__guarded_authorizer,
            )
            self.__learnfactory_authorizer = self.__guarded_authorizer
            return self.__authorizer_guard_violation_reason

    def _end_authorizer_guard(
        self,
        capability: _AuthorizerGuardCapability,
    ) -> str | None:
        """Restore the exact prior callback and retire the capability."""

        with self.__authorizer_lock:
            if capability is not self.__authorizer_guard:
                raise AuthorizerGuardError(
                    "invalid database authorizer guard capability"
                )
            previous = self.__guarded_previous_authorizer
            sqlite3.Connection.set_authorizer(  # type: ignore[arg-type]
                self,
                previous,
            )
            self.__learnfactory_authorizer = previous
            violation = self.__authorizer_guard_violation_reason
            self.__authorizer_guard = None
            self.__guarded_authorizer = None
            self.__guarded_previous_authorizer = None
            self.__authorizer_guard_violation_reason = None
            return violation

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

    def __init__(
        self,
        path: Path,
        migrations: Path,
        *,
        busy_timeout_seconds: float = 30,
        read_only: bool = False,
    ):
        if busy_timeout_seconds <= 0:
            raise ValueError("busy_timeout_seconds must be positive")
        self.path = path
        self.migrations = migrations
        self.busy_timeout_seconds = float(busy_timeout_seconds)
        self.read_only = read_only
        self._setup_lock = threading.Lock()
        self._parent_ready = False

    def connect(
        self,
        *,
        busy_timeout_seconds: float | None = None,
    ) -> sqlite3.Connection:
        effective_busy_timeout = (
            self.busy_timeout_seconds
            if busy_timeout_seconds is None
            else float(busy_timeout_seconds)
        )
        if effective_busy_timeout <= 0:
            raise ValueError("connection busy timeout must be positive")
        if self.read_only:
            target: str | Path = self.path.resolve().as_uri() + "?mode=ro"
        else:
            with self._setup_lock:
                if not self._parent_ready:
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    self._parent_ready = True
            target = self.path
        connection = sqlite3.connect(
            target,
            timeout=effective_busy_timeout,
            isolation_level=None,
            check_same_thread=False,
            # set_authorizer() does not re-authorize Python's cached prepared
            # statements on SQLite 3.26. Publication callbacks temporarily
            # narrow authority, so connection-local statement caching would
            # let a query prepared before that boundary bypass the policy.
            cached_statements=0,
            factory=ClosingConnection,
            uri=self.read_only,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            f"PRAGMA busy_timeout = {max(1, int(effective_busy_timeout * 1000))}"
        )
        if self.read_only:
            connection.execute("PRAGMA query_only = ON")
        else:
            connection.execute("PRAGMA synchronous = FULL")
        return connection

    def readonly(self) -> Database:
        """Return a connection factory that cannot create or mutate the database."""

        return Database(
            self.path,
            self.migrations,
            busy_timeout_seconds=self.busy_timeout_seconds,
            read_only=True,
        )

    def _migration_specs(self) -> list[_Migration]:
        specifications: list[_Migration] = []
        for path in sorted(self.migrations.glob("[0-9][0-9][0-9]_*.sql")):
            content = path.read_text(encoding="utf-8")
            specifications.append(
                _Migration(
                    path=path,
                    version=path.name,
                    content=content,
                    checksum=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                )
            )
        return specifications

    @staticmethod
    def _validate_applied_migrations(
        specifications: list[_Migration], existing: dict[str, str]
    ) -> None:
        for migration in specifications:
            checksum = existing.get(migration.version)
            if checksum is not None and checksum != migration.checksum:
                raise MigrationError(
                    f"applied migration changed: {migration.version}"
                )

    @staticmethod
    def _read_migration_ledger(
        connection: sqlite3.Connection,
    ) -> tuple[bool, dict[str, str]]:
        table_exists = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='schema_migrations'
            """
        ).fetchone() is not None
        existing = (
            {
                str(row["version"]): str(row["checksum"])
                for row in connection.execute(
                    "SELECT version,checksum FROM schema_migrations"
                )
            }
            if table_exists
            else {}
        )
        return table_exists, existing

    def verify_migrations(self) -> None:
        """Verify schema compatibility without creating a file or taking a write lock."""

        specifications = self._migration_specs()
        try:
            with self.readonly().connect() as connection:
                table = connection.execute(
                    """
                    SELECT 1 FROM sqlite_master
                    WHERE type='table' AND name='schema_migrations'
                    """
                ).fetchone()
                if table is None:
                    raise MigrationError(
                        "database is not initialized; run `learnfactory init`"
                    )
                existing = {
                    str(row["version"]): str(row["checksum"])
                    for row in connection.execute(
                        "SELECT version,checksum FROM schema_migrations"
                    )
                }
        except MigrationError:
            raise
        except sqlite3.Error as error:
            raise MigrationError(
                "database is not initialized or is unreadable; "
                "run `learnfactory init`"
            ) from error
        self._validate_applied_migrations(specifications, existing)
        missing = [
            migration.version
            for migration in specifications
            if migration.version not in existing
        ]
        if missing:
            raise MigrationError(
                "database schema is out of date; run `learnfactory init` "
                f"(missing {', '.join(missing)})"
            )

    def migrate(self) -> list[str]:
        if self.read_only:
            raise MigrationError("cannot migrate through a read-only database")
        specifications = self._migration_specs()
        applied: list[str] = []
        try:
            with self.connect() as connection:
                _table_exists, observed = self._read_migration_ledger(connection)
        except sqlite3.Error as error:
            raise MigrationError("failed to inspect migration ledger") from error
        # Never mutate journal state before proving the existing migration
        # ledger is checksum-compatible with this executable.
        self._validate_applied_migrations(specifications, observed)
        schema_current = all(
            migration.version in observed for migration in specifications
        )
        self._normalize_rollback_journal()
        if schema_current:
            return applied

        with self.connect() as connection:
            current_version = "schema_migrations"
            try:
                # Concurrent starters re-check the complete ledger behind this
                # single lock before applying anything.
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version TEXT PRIMARY KEY,
                        checksum TEXT NOT NULL,
                        applied_at REAL NOT NULL
                    )
                    """
                )
                _table_exists, existing = self._read_migration_ledger(connection)
                self._validate_applied_migrations(specifications, existing)
                for migration in specifications:
                    current_version = migration.version
                    if migration.version in existing:
                        continue
                    for statement in _sql_statements(migration.content):
                        connection.execute(statement)
                    connection.execute(
                        """
                        INSERT INTO schema_migrations(version,checksum,applied_at)
                        VALUES (?,?,?)
                        """,
                        (migration.version, migration.checksum, now()),
                    )
                    applied.append(migration.version)
                connection.commit()
            except MigrationError:
                if connection.in_transaction:
                    connection.rollback()
                raise
            except sqlite3.Error as error:
                if connection.in_transaction:
                    connection.rollback()
                raise MigrationError(
                    f"migration {current_version} failed: {error}"
                ) from error
        return applied

    def _normalize_rollback_journal(self) -> None:
        """Converge an incompatible persistent journal mode across processes.

        SQLite 3.26 can ignore the configured busy handler for journal-mode
        changes, and an idle open WAL connection can prevent a peer from
        normalizing the database. Each failed attempt therefore closes its
        connection before a bounded backoff, then reopens and rereads the
        durable mode. No ordinary connection assigns journal mode.
        """

        deadline = time.monotonic() + max(1.0, self.busy_timeout_seconds)
        attempt = 0
        last_error: sqlite3.OperationalError | None = None
        while True:
            remaining = deadline - time.monotonic()
            if remaining < 0.004:
                raise MigrationError(
                    "timed out normalizing SQLite journal mode to DELETE"
                ) from last_error
            attempt_timeout = min(0.05, remaining / 4.0)
            try:
                with self.connect(
                    busy_timeout_seconds=attempt_timeout
                ) as connection:
                    current = str(
                        connection.execute("PRAGMA journal_mode").fetchone()[0]
                    ).lower()
                    if current == "delete":
                        return
                    normalized = str(
                        connection.execute(
                            "PRAGMA journal_mode = DELETE"
                        ).fetchone()[0]
                    ).lower()
                    if normalized == "delete":
                        return
                    last_error = sqlite3.OperationalError(
                        f"journal mode remained {normalized!r}"
                    )
            except sqlite3.OperationalError as error:
                if not self._transient_lock_error(error):
                    raise MigrationError(
                        "failed to inspect or normalize SQLite journal mode"
                    ) from error
                last_error = error
            if time.monotonic() >= deadline:
                raise MigrationError(
                    "timed out normalizing SQLite journal mode to DELETE"
                ) from last_error
            attempt += 1
            phase_seed = (os.getpid() * 31) ^ threading.get_ident()
            phase = 1.0 + ((phase_seed % 31) / 100.0)
            sleep_budget = max(0.0, deadline - time.monotonic())
            time.sleep(
                min(
                    sleep_budget,
                    0.05,
                    0.002 * (2 ** min(attempt, 5)) * phase,
                )
            )

    @staticmethod
    def _transient_lock_error(error: sqlite3.OperationalError) -> bool:
        code = getattr(error, "sqlite_errorcode", None)
        if isinstance(code, int) and (code & 0xFF) in {
            sqlite3.SQLITE_BUSY,
            sqlite3.SQLITE_LOCKED,
        }:
            return True
        message = str(error).lower()
        return "locked" in message or "busy" in message

    @contextlib.contextmanager
    def transaction(
        self,
        *,
        immediate: bool = False,
        busy_timeout_seconds: float | None = None,
    ) -> Iterator[sqlite3.Connection]:
        if self.read_only:
            raise sqlite3.OperationalError(
                "write transaction requested through a read-only database"
            )
        if busy_timeout_seconds is not None and busy_timeout_seconds <= 0:
            raise ValueError("transaction busy timeout must be positive")
        connection = self.connect(
            busy_timeout_seconds=busy_timeout_seconds
        )
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

    @contextlib.contextmanager
    def read_transaction(self) -> Iterator[sqlite3.Connection]:
        """Hold a consistent query-only snapshot without taking a write lock."""

        connection = self.connect()
        try:
            connection.execute("BEGIN")
            yield connection
            connection.rollback()
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

    def set_system_value(
        self,
        key: str,
        value: Any,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        values = (key, canonical_json(value), now())
        statement = """
            INSERT INTO system_state(key,value_json,updated_at) VALUES (?,?,?)
            ON CONFLICT(key) DO UPDATE SET
                value_json=excluded.value_json, updated_at=excluded.updated_at
        """
        if connection is not None:
            connection.execute(statement, values)
            return
        with self.transaction(immediate=True) as owned:
            owned.execute(statement, values)
