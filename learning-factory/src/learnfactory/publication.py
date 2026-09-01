"""Least-privilege SQLite surface for atomic artifact publication callbacks.

Callbacks share the authoritative artifact transaction because source catalog
and learner evidence rows must not get ahead of the artifact that supports
them.  They do not receive the owning ``sqlite3.Connection``: this module
exposes a small typed facade and installs a SQLite authorizer as a second,
independent enforcement layer for the duration of the callback.
"""

from __future__ import annotations

import contextlib
import re
import sqlite3
import threading
from collections.abc import Iterable, Iterator, Mapping, Sequence
from enum import Enum
from typing import Any, Never, Protocol, TypeAlias

from .db import (
    AuthorizerGuardError,
    ClosingConnection,
    _AuthorizerGuardCapability,
)


SqlParameters: TypeAlias = Sequence[Any] | Mapping[str, Any]


class PublicationAccessError(RuntimeError):
    """A publication callback attempted authority outside its contract."""


class PublicationScope(str, Enum):
    """Orchestrator-selected database authority for one callback role."""

    SOURCE_INGESTION = "source_ingestion"
    LEARNER_EVIDENCE = "learner_evidence"


class PublicationCursor(Protocol):
    """Cursor operations available to a publication callback."""

    @property
    def connection(self) -> PublicationConnection: ...

    @property
    def rowcount(self) -> int: ...

    @property
    def lastrowid(self) -> int | None: ...

    @property
    def description(self) -> object: ...

    def execute(
        self, statement: str, parameters: SqlParameters = ()
    ) -> PublicationCursor: ...

    def executemany(
        self, statement: str, parameters: Iterable[SqlParameters]
    ) -> PublicationCursor: ...

    def fetchone(self) -> sqlite3.Row | None: ...

    def fetchmany(self, size: int | None = None) -> list[sqlite3.Row]: ...

    def fetchall(self) -> list[sqlite3.Row]: ...

    def __iter__(self) -> Iterator[sqlite3.Row]: ...


class PublicationConnection(Protocol):
    """The complete database contract available during publication."""

    @property
    def in_transaction(self) -> bool: ...

    def execute(
        self, statement: str, parameters: SqlParameters = ()
    ) -> PublicationCursor: ...

    def executemany(
        self, statement: str, parameters: Iterable[SqlParameters]
    ) -> PublicationCursor: ...

    def cursor(self) -> PublicationCursor: ...


# These are the only durable domains publication hooks own.  The scheduler
# chooses the scope; a callback cannot request one or move laterally from
# catalog data into learner data (or vice versa).
_SOURCE_WRITE_TABLES = frozenset(
    {
        "sources",
        "courses",
        "course_units",
        "curriculum_edges",
        "build_projects",
        "events",
    }
)
_LEARNER_WRITE_TABLES = frozenset(
    {
        "attempts",
        "evaluations",
        "learner_knowledge",
        "knowledge_evidence",
        "students",
        "events",
    }
)
_EVENT_FOREIGN_KEY_READ_TABLES = frozenset({"jobs", "workers"})
# SQLite authorizes reads of child keys while compiling writes to a referenced
# parent.  Source ingestion may therefore inspect immutable BYOX baseline keys
# to satisfy the `byox_baseline_snapshots.source_id -> sources.source_id`
# constraint, but it still has no authority to mutate that S2 ledger.
_SOURCE_FOREIGN_KEY_READ_TABLES = frozenset({"byox_baseline_snapshots"})
_SCOPE_WRITE_TABLES = {
    PublicationScope.SOURCE_INGESTION: _SOURCE_WRITE_TABLES,
    PublicationScope.LEARNER_EVIDENCE: _LEARNER_WRITE_TABLES,
}
_SCOPE_READ_TABLES = {
    PublicationScope.SOURCE_INGESTION: (
        _SOURCE_WRITE_TABLES
        | _EVENT_FOREIGN_KEY_READ_TABLES
        | _SOURCE_FOREIGN_KEY_READ_TABLES
    ),
    # Learner activation validates the examiner result and declared student
    # dependency in the same transaction that records evidence.  These
    # control-plane tables are read-only.  SQLite also authorizes both event
    # foreign-key parents while compiling an insertion, including NULL keys.
    PublicationScope.LEARNER_EVIDENCE: (
        _LEARNER_WRITE_TABLES
        | _EVENT_FOREIGN_KEY_READ_TABLES
        | frozenset(
            {
                "validations",
                "job_dependencies",
                "artifacts",
                "job_runs",
                # Repeated-concept activation recomputes confidence from only
                # non-invalidated evidence.  This ledger remains read-only;
                # its attempt-level sibling is deliberately not exposed.
                "learner_evidence_invalidations",
            }
        )
    ),
}

_FORBIDDEN_FIRST_KEYWORDS = frozenset(
    {
        "ALTER",
        "ANALYZE",
        "ATTACH",
        "BEGIN",
        "COMMIT",
        "CREATE",
        "DETACH",
        "DROP",
        "END",
        "PRAGMA",
        "REINDEX",
        "RELEASE",
        "ROLLBACK",
        "SAVEPOINT",
        "VACUUM",
    }
)
_LEADING_SQL = re.compile(
    r"(?:\s+|--[^\n]*(?:\n|$)|/\*.*?\*/)*([A-Za-z]+)", re.DOTALL
)
_DANGEROUS_FUNCTIONS = frozenset({"load_extension", "readfile", "writefile"})


class _PublicationPolicy:
    def __init__(self, scope: PublicationScope) -> None:
        self.scope = scope
        self.write_tables = _SCOPE_WRITE_TABLES[scope]
        self.read_tables = _SCOPE_READ_TABLES[scope]
        self.denial: str | None = None
        self.first_violation: str | None = None
        # A callback may retain a facade or start a background thread.  The
        # same reentrant lock therefore protects both the capability lifetime
        # and every access to the raw SQLite objects.  Reentrancy is required
        # because sqlite3 invokes ``authorize`` synchronously while execute()
        # already holds this lock.
        self.__lifetime_lock = threading.RLock()
        self.__active = False
        self.__connection: ClosingConnection | None = None
        self.__guard_capability: _AuthorizerGuardCapability | None = None

    def _guard_context(
        self,
    ) -> tuple[ClosingConnection, _AuthorizerGuardCapability]:
        connection = self.__connection
        capability = self.__guard_capability
        if connection is None or capability is None:
            raise AuthorizerGuardError(
                "publication database authorizer guard is unavailable"
            )
        return connection, capability

    def _reassert_guard(self) -> None:
        """Reinstall the guarded authorizer and surface tracked mutation."""

        connection, capability = self._guard_context()
        try:
            violation = connection._reassert_authorizer_guard(capability)
        except BaseException:
            self.reject(
                "publication database authorizer could not be reasserted"
            )
        if violation is not None:
            self.reject(violation)

    def install(self, connection: ClosingConnection) -> None:
        """Activate the capability and install its authorizer atomically."""

        with self.__lifetime_lock:
            if self.__active:
                raise PublicationAccessError(
                    "publication capability is already active"
                )
            self.__active = True
            try:
                capability, _previous = connection._begin_authorizer_guard(
                    self.authorize,
                )
            except BaseException:
                self.__active = False
                raise
            self.__connection = connection
            self.__guard_capability = capability

    def revoke_and_restore(self, connection: ClosingConnection) -> None:
        """Revoke before restoring prior authority under the operation lock."""

        with self.__lifetime_lock:
            self.__active = False
            # Keep the lock through restoration.  Otherwise a retained facade
            # could pass an active check, pause, and execute after the narrower
            # authorizer has been removed.
            guarded_connection, capability = self._guard_context()
            if guarded_connection is not connection:
                raise AuthorizerGuardError(
                    "publication database authorizer connection changed"
                )
            violation = connection._end_authorizer_guard(capability)
            self.__connection = None
            self.__guard_capability = None
            if violation is not None:
                self.deny(violation)

    @contextlib.contextmanager
    def operation(self) -> Iterator[None]:
        """Serialize one complete facade operation with capability revocation."""

        with self.__lifetime_lock:
            if not self.__active:
                raise PublicationAccessError(
                    "publication capability is no longer active"
                )
            # This is intentionally unconditional. sqlite3 cannot expose the
            # currently installed authorizer, and a direct invocation of the
            # base descriptor bypasses ClosingConnection's Python tracking.
            self._reassert_guard()
            yield

    def violation(self) -> str | None:
        with self.__lifetime_lock:
            return self.first_violation

    def reset_denial(self) -> None:
        with self.__lifetime_lock:
            self.denial = None

    def deny(self, reason: str) -> int:
        with self.__lifetime_lock:
            self.denial = reason
            if self.first_violation is None:
                self.first_violation = reason
            return sqlite3.SQLITE_DENY

    def reject(self, reason: str) -> Never:
        self.deny(reason)
        raise PublicationAccessError(reason)

    def authorize(
        self,
        action: int,
        argument1: str | None,
        argument2: str | None,
        database_name: str | None,
        trigger_name: str | None,
    ) -> int:
        with self.__lifetime_lock:
            if not self.__active:
                # If restoration itself fails, Database.transaction still
                # needs one safe path to roll back before closing this
                # connection. Retained facade operations never reach SQLite
                # after revocation because operation() rejects them first.
                if (
                    action == sqlite3.SQLITE_TRANSACTION
                    and (argument1 or "").upper() == "ROLLBACK"
                ):
                    return sqlite3.SQLITE_OK
                return self.deny(
                    "publication database authorizer ran after capability revocation"
                )
            if action in {
                sqlite3.SQLITE_INSERT,
                sqlite3.SQLITE_UPDATE,
                sqlite3.SQLITE_DELETE,
            }:
                table = (argument1 or "").lower()
                if (
                    database_name not in {None, "main"}
                    or table not in self.write_tables
                ):
                    return self.deny(
                        f"publication write to {database_name}.{table} is forbidden"
                    )
            elif action == sqlite3.SQLITE_READ:
                table = (argument1 or "").lower()
                # This environment's SQLite 3.26 reports None rather than
                # "main" for ordinary SELECT compilation. Attached DBs retain
                # names.
                if (
                    database_name not in {None, "main"}
                    or table not in self.read_tables
                ):
                    return self.deny(
                        f"publication read from {database_name}.{table} is forbidden"
                    )
            elif action == sqlite3.SQLITE_FUNCTION:
                function = (argument2 or argument1 or "").lower()
                if function in _DANGEROUS_FUNCTIONS:
                    return self.deny(
                        f"publication SQL function {function} is forbidden"
                    )
            elif action != sqlite3.SQLITE_SELECT:
                return self.deny(
                    "publication SQL operation is forbidden "
                    f"(authorizer action {action}, object {argument1!r})"
                )

            return sqlite3.SQLITE_OK


def _check_statement(statement: str, policy: _PublicationPolicy) -> None:
    if not isinstance(statement, str) or not statement.strip():
        policy.reject("publication SQL must be a nonempty string")
    match = _LEADING_SQL.match(statement)
    if match is None:
        policy.reject("publication SQL has no recognizable statement")
    keyword = match.group(1).upper()
    if keyword in _FORBIDDEN_FIRST_KEYWORDS:
        policy.reject(f"publication SQL statement {keyword} is forbidden")


def _translate_authorizer_denial(
    error: sqlite3.DatabaseError, policy: _PublicationPolicy
) -> None:
    error_code = getattr(error, "sqlite_errorcode", None)
    sqlite_auth = (
        isinstance(error_code, int)
        and (error_code & 0xFF) == sqlite3.SQLITE_AUTH
    )
    message = str(error).lower()
    if (
        policy.denial is not None
        or sqlite_auth
        or "not authorized" in message
        or "is prohibited" in message
    ):
        raise PublicationAccessError(
            policy.denial or "publication SQL was denied by the database authorizer"
        ) from error


class _RestrictedPublicationIterator:
    """Row iterator whose complete public object graph remains restricted."""

    __slots__ = ("__cursor", "__policy")

    def __init__(
        self,
        cursor: _RestrictedPublicationCursor,
        policy: _PublicationPolicy,
    ) -> None:
        self.__cursor = cursor
        self.__policy = policy

    @property
    def connection(self) -> PublicationConnection:
        # Match cursor chaining without exposing sqlite3.Cursor.connection.
        with self.__policy.operation():
            return self.__cursor.connection

    def __iter__(self) -> _RestrictedPublicationIterator:
        with self.__policy.operation():
            return self

    def __next__(self) -> sqlite3.Row:
        row = self.__cursor.fetchone()
        if row is None:
            raise StopIteration
        return row


class _RestrictedPublicationCursor:
    __slots__ = ("__cursor", "__connection", "__policy")

    def __init__(
        self,
        cursor: sqlite3.Cursor,
        connection: _RestrictedPublicationConnection,
        policy: _PublicationPolicy,
    ) -> None:
        self.__cursor = cursor
        self.__connection = connection
        self.__policy = policy

    @property
    def connection(self) -> PublicationConnection:
        # Never expose sqlite3.Cursor.connection, which is the owning raw
        # connection.  Returning the restricted facade preserves chaining.
        with self.__policy.operation():
            return self.__connection

    @property
    def rowcount(self) -> int:
        with self.__policy.operation():
            return int(self.__cursor.rowcount)

    @property
    def lastrowid(self) -> int | None:
        with self.__policy.operation():
            value = self.__cursor.lastrowid
            return int(value) if value is not None else None

    @property
    def description(self) -> object:
        with self.__policy.operation():
            return self.__cursor.description

    def execute(
        self, statement: str, parameters: SqlParameters = ()
    ) -> _RestrictedPublicationCursor:
        with self.__policy.operation():
            _check_statement(statement, self.__policy)
            self.__policy.reset_denial()
            self.__policy._reassert_guard()
            try:
                self.__cursor.execute(statement, parameters)
            except sqlite3.DatabaseError as error:
                _translate_authorizer_denial(error, self.__policy)
                raise
            return self

    def executemany(
        self, statement: str, parameters: Iterable[SqlParameters]
    ) -> _RestrictedPublicationCursor:
        with self.__policy.operation():
            _check_statement(statement, self.__policy)
            self.__policy.reset_denial()
            self.__policy._reassert_guard()
            try:
                self.__cursor.executemany(statement, parameters)
            except sqlite3.DatabaseError as error:
                _translate_authorizer_denial(error, self.__policy)
                raise
            return self

    def fetchone(self) -> sqlite3.Row | None:
        with self.__policy.operation():
            return self.__cursor.fetchone()

    def fetchmany(self, size: int | None = None) -> list[sqlite3.Row]:
        with self.__policy.operation():
            if size is None:
                return self.__cursor.fetchmany()
            return self.__cursor.fetchmany(size)

    def fetchall(self) -> list[sqlite3.Row]:
        with self.__policy.operation():
            return self.__cursor.fetchall()

    def __iter__(self) -> Iterator[sqlite3.Row]:
        # sqlite3.Cursor.__iter__ returns the raw cursor itself, whose public
        # ``connection`` attribute would expose the owning transaction. Keep
        # iteration on a facade that fetches only through this wrapper.
        with self.__policy.operation():
            return _RestrictedPublicationIterator(self, self.__policy)

    def close(self) -> None:
        with self.__policy.operation():
            self.__policy.reject("publication callbacks cannot close cursors")

    def executescript(self, _script: str) -> None:
        with self.__policy.operation():
            self.__policy.reject("publication callbacks cannot execute SQL scripts")


class _RestrictedPublicationConnection:
    __slots__ = ("__connection", "__policy")

    def __init__(
        self, connection: ClosingConnection, policy: _PublicationPolicy
    ) -> None:
        self.__connection = connection
        self.__policy = policy

    @property
    def in_transaction(self) -> bool:
        with self.__policy.operation():
            return bool(self.__connection.in_transaction)

    def cursor(self) -> PublicationCursor:
        with self.__policy.operation():
            return _RestrictedPublicationCursor(
                self.__connection.cursor(), self, self.__policy
            )

    def execute(
        self, statement: str, parameters: SqlParameters = ()
    ) -> PublicationCursor:
        with self.__policy.operation():
            cursor = self.cursor()
            return cursor.execute(statement, parameters)

    def executemany(
        self, statement: str, parameters: Iterable[SqlParameters]
    ) -> PublicationCursor:
        with self.__policy.operation():
            cursor = self.cursor()
            return cursor.executemany(statement, parameters)

    def _denied(self, operation: str) -> Never:
        with self.__policy.operation():
            self.__policy.reject(
                f"publication callbacks cannot {operation} the owning connection"
            )

    def commit(self) -> None:
        self._denied("commit")

    def rollback(self) -> None:
        self._denied("roll back")

    def close(self) -> None:
        self._denied("close")

    def executescript(self, _script: str) -> None:
        self._denied("execute SQL scripts on")

    def set_authorizer(self, _callback: object) -> None:
        self._denied("replace the authorizer on")

    def enable_load_extension(self, _enabled: bool) -> None:
        self._denied("enable extensions on")

    def load_extension(self, _path: str) -> None:
        self._denied("load extensions into")

    def create_function(self, *args: object, **kwargs: object) -> None:
        self._denied("register functions on")

    def create_aggregate(self, *args: object, **kwargs: object) -> None:
        self._denied("register aggregates on")

    def create_collation(self, *args: object, **kwargs: object) -> None:
        self._denied("register collations on")

    def set_progress_handler(self, *args: object, **kwargs: object) -> None:
        self._denied("replace the progress handler on")

    def set_trace_callback(self, *args: object, **kwargs: object) -> None:
        self._denied("replace the trace callback on")

    def interrupt(self) -> None:
        self._denied("interrupt")

    def __enter__(self) -> PublicationConnection:
        self._denied("enter a transaction context on")
        raise AssertionError("unreachable")

    def __exit__(self, *args: object) -> None:
        self._denied("exit a transaction context on")


@contextlib.contextmanager
def restricted_publication_connection(
    connection: sqlite3.Connection,
    scope: PublicationScope,
) -> Iterator[PublicationConnection]:
    """Install callback policy and yield a facade without raw DB authority."""

    if not isinstance(connection, ClosingConnection):
        raise PublicationAccessError(
            "publication requires a tracked database connection so its authorizer can be restored"
        )
    if not isinstance(scope, PublicationScope):
        raise PublicationAccessError("publication scope must be selected by the orchestrator")
    policy = _PublicationPolicy(scope)
    try:
        policy.install(connection)
    except AuthorizerGuardError:
        # Do not expose details from an existing callback or a private guard
        # implementation through the public publication API.
        raise PublicationAccessError(
            "publication requires a controller-owned connection without a "
            "tracked pre-existing database authorizer"
        ) from None
    callback_returned = False
    try:
        yield _RestrictedPublicationConnection(connection, policy)
        callback_returned = True
    finally:
        policy.revoke_and_restore(connection)
    violation = policy.violation()
    if callback_returned and violation is not None:
        raise PublicationAccessError(
            "publication callback suppressed a denied operation: "
            + violation
        )
