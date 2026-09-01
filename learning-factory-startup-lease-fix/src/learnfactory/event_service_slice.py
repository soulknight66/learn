from __future__ import annotations

import json
import sqlite3
from difflib import unified_diff
from pathlib import Path
from textwrap import dedent
from typing import Any

from .db import Database
from .util import redact, tree_sha256
from .vertical_slices import SliceResult


_DEFAULT_PROVENANCE = {
    "derivation": "agent-generated cross-source synthesis",
    "source_name": "CSDIY and Build Your Own X catalog synthesis",
    "upstream_url": "local ingested source catalogs",
    "commit_hash": "recorded by the learning-factory source catalog",
    "license": "new generated material; source catalogs and linked works retain their licenses",
    "source_reference": "production event-processing service synthesis",
}


def _clean(value: object, *, limit: int = 2_000) -> str:
    return redact(str(value), limit=limit).strip()


def _target(workspace: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or not candidate.parts or any(
        part in {"", ".", ".."} for part in candidate.parts
    ):
        raise ValueError(f"unsafe generated path: {relative!r}")
    root = workspace.resolve()
    path = workspace / candidate
    try:
        path.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError(f"generated path escapes workspace: {relative!r}") from error
    current = workspace
    for part in candidate.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"generated path traverses symlink: {relative!r}")
        current.mkdir(exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"refusing to overwrite symlink: {relative!r}")
    return path


def _write(workspace: Path, relative: str, content: str) -> None:
    rendered = dedent(content).lstrip("\n")
    if rendered and not rendered.endswith("\n"):
        rendered += "\n"
    _target(workspace, relative).write_text(rendered, encoding="utf-8", newline="\n")


def _write_json(workspace: Path, relative: str, value: object) -> None:
    _write(
        workspace,
        relative,
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False),
    )


def _provenance(db: Database, payload: dict[str, Any]) -> dict[str, Any]:
    """Resolve catalog facts through an allowlist and label all synthesis honestly."""

    result: dict[str, Any] = dict(_DEFAULT_PROVENANCE)
    result["lookup_status"] = "generated synthesis defaults"
    source_ids: list[str] = []
    raw_ids = payload.get("source_ids")
    if isinstance(raw_ids, list):
        source_ids = [_clean(value, limit=200) for value in raw_ids[:10] if value]
    elif payload.get("source_id"):
        source_ids = [_clean(payload["source_id"], limit=200)]
    catalog_sources: list[dict[str, str]] = []
    try:
        with db.connect() as connection:
            if source_ids:
                for source_id in source_ids:
                    row = connection.execute(
                        """
                        SELECT source_id,name,upstream_url,commit_hash,license
                        FROM sources WHERE source_id=? AND is_active=1
                        """,
                        (source_id,),
                    ).fetchone()
                    if row is not None:
                        catalog_sources.append(
                            {
                                key: _clean(row[key])
                                for key in (
                                    "source_id",
                                    "name",
                                    "upstream_url",
                                    "commit_hash",
                                    "license",
                                )
                                if row[key] is not None
                            }
                        )
            else:
                rows = connection.execute(
                    """
                    SELECT source_id,name,upstream_url,commit_hash,license
                    FROM sources
                    WHERE is_active=1 AND (
                        lower(type) IN ('csdiy','build_your_own_x','build-your-own-x')
                        OR lower(name) LIKE '%csdiy%'
                        OR lower(name) LIKE '%build your own x%'
                        OR lower(name) LIKE '%build-your-own-x%'
                    )
                    ORDER BY source_id LIMIT 10
                    """
                ).fetchall()
                for row in rows:
                    catalog_sources.append(
                        {
                            key: _clean(row[key])
                            for key in (
                                "source_id",
                                "name",
                                "upstream_url",
                                "commit_hash",
                                "license",
                            )
                            if row[key] is not None
                        }
                    )
    except sqlite3.Error as error:
        result["lookup_status"] = f"catalog lookup unavailable: {_clean(error, limit=300)}"
    supplied = payload.get("provenance")
    if isinstance(supplied, dict):
        aliases = {
            "source": "source_name",
            "upstream": "upstream_url",
            "commit": "commit_hash",
            "license": "license",
            "source_reference": "source_reference",
        }
        for incoming, outgoing in aliases.items():
            if supplied.get(incoming):
                result[outgoing] = _clean(supplied[incoming])
        result["lookup_status"] = "unverified job provenance allowlist"
    if catalog_sources:
        result["source_name"] = " + ".join(
            source.get("name", source["source_id"]) for source in catalog_sources
        )
        for field in ("upstream_url", "commit_hash", "license"):
            values = [source[field] for source in catalog_sources if source.get(field)]
            if values:
                result[field] = " + ".join(values)
        result["lookup_status"] = "catalog-linked source records"
        result["provenance_status"] = "CATALOG_LINKED"
    else:
        result["provenance_status"] = "INCOMPLETE"
    result["catalog_sources"] = catalog_sources
    result["job_id"] = _clean(payload.get("job_id", "unrecorded"), limit=200)
    # This is intentionally not overrideable by a payload.
    result["derivation"] = "agent-generated cross-source synthesis"
    return result


_MIGRATION = r'''
    CREATE TABLE messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        idempotency_key TEXT NOT NULL UNIQUE,
        payload_json TEXT NOT NULL,
        state TEXT NOT NULL CHECK (state IN ('READY','CLAIMED','RETRY_WAIT','DONE','DEAD')),
        attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
        available_at REAL NOT NULL,
        lease_owner TEXT,
        lease_token TEXT,
        lease_expires_at REAL,
        last_error TEXT,
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL,
        dead_lettered_at REAL,
        CHECK (
            (state = 'CLAIMED' AND lease_owner IS NOT NULL AND lease_token IS NOT NULL
                               AND lease_expires_at IS NOT NULL)
            OR
            (state <> 'CLAIMED' AND lease_owner IS NULL AND lease_token IS NULL
                                AND lease_expires_at IS NULL)
        )
    );

    CREATE INDEX messages_dispatch
        ON messages(state, available_at, message_id);

    CREATE TABLE effects (
        message_id INTEGER PRIMARY KEY REFERENCES messages(message_id),
        effect_key TEXT NOT NULL UNIQUE,
        result_json TEXT NOT NULL,
        applied_at REAL NOT NULL
    );

    CREATE TABLE dead_letters (
        dead_letter_id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL REFERENCES messages(message_id),
        payload_json TEXT NOT NULL,
        attempts INTEGER NOT NULL,
        reason TEXT NOT NULL,
        dead_lettered_at REAL NOT NULL,
        requeued_at REAL
    );

    CREATE UNIQUE INDEX dead_letters_one_active
        ON dead_letters(message_id) WHERE requeued_at IS NULL;

    CREATE INDEX dead_letters_page
        ON dead_letters(requeued_at, dead_letter_id);
'''


_EVENT_SERVICE = r'''
    from __future__ import annotations

    import argparse
    import json
    import queue
    import re
    import secrets
    import sqlite3
    import threading
    import time
    from dataclasses import asdict, dataclass
    from pathlib import Path
    from typing import Any, Callable, Iterable


    _KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
    _STATES = ("READY", "CLAIMED", "RETRY_WAIT", "DONE", "DEAD")


    class LeaseLost(RuntimeError):
        """The delivery is no longer owned by this worker."""


    class InjectedCrash(RuntimeError):
        """A deliberate process-crash boundary used only by fault tests."""


    @dataclass(frozen=True)
    class Delivery:
        message_id: int
        idempotency_key: str
        payload: dict[str, Any]
        attempt: int
        lease_owner: str
        lease_token: str
        lease_expires_at: float


    class JsonLogger:
        """Small structured logger with an injectable sink for deterministic tests."""

        def __init__(
            self,
            sink: Callable[[str], None] | None = None,
            clock: Callable[[], float] = time.time,
        ) -> None:
            self._sink = sink or print
            self._clock = clock

        def emit(self, level: str, event: str, **fields: object) -> None:
            record = {"ts": self._clock(), "level": level, "event": event, **fields}
            self._sink(json.dumps(record, sort_keys=True, separators=(",", ":")))


    class Metrics:
        """Thread-safe counters; a real deployment would export these externally."""

        def __init__(self) -> None:
            self._lock = threading.Lock()
            self._counters: dict[str, int] = {}

        def increment(self, name: str, amount: int = 1) -> None:
            with self._lock:
                self._counters[name] = self._counters.get(name, 0) + amount

        def snapshot(self) -> dict[str, int]:
            with self._lock:
                return dict(sorted(self._counters.items()))


    class EventService:
        """SQLite-backed, at-least-once work queue with durable ownership.

        The local ``effects`` table demonstrates an idempotent consumer. An arbitrary
        remote side effect would require its own idempotency contract; SQLite cannot
        make a transaction atomic with an unrelated service.
        """

        def __init__(
            self,
            path: str | Path,
            *,
            clock: Callable[[], float] = time.time,
            max_attempts: int = 3,
            base_backoff: float = 1.0,
            max_payload_bytes: int = 65_536,
        ) -> None:
            if max_attempts < 1:
                raise ValueError("max_attempts must be positive")
            if base_backoff < 0:
                raise ValueError("base_backoff must be nonnegative")
            self.path = Path(path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.clock = clock
            self.max_attempts = max_attempts
            self.base_backoff = base_backoff
            self.max_payload_bytes = max_payload_bytes
            self.migrate()

        def _connect(self) -> sqlite3.Connection:
            connection = sqlite3.connect(
                self.path,
                timeout=10,
                isolation_level=None,
                check_same_thread=False,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=10000")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA journal_mode=DELETE")
            return connection

        @staticmethod
        def _statements(script: str) -> Iterable[str]:
            pending = ""
            for line in script.splitlines(keepends=True):
                pending += line
                if sqlite3.complete_statement(pending):
                    if pending.strip():
                        yield pending
                    pending = ""
            if pending.strip():
                raise RuntimeError("incomplete migration")

        def migrate(self) -> None:
            migration_dir = Path(__file__).resolve().parent / "migrations"
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations(
                        version TEXT PRIMARY KEY,
                        applied_at REAL NOT NULL
                    )
                    """
                )
                for path in sorted(migration_dir.glob("[0-9][0-9][0-9]_*.sql")):
                    connection.execute("BEGIN IMMEDIATE")
                    try:
                        row = connection.execute(
                            "SELECT 1 FROM schema_migrations WHERE version=?", (path.name,)
                        ).fetchone()
                        if row is None:
                            for statement in self._statements(path.read_text(encoding="utf-8")):
                                connection.execute(statement)
                            connection.execute(
                                "INSERT INTO schema_migrations(version,applied_at) VALUES (?,?)",
                                (path.name, self.clock()),
                            )
                        connection.commit()
                    except BaseException:
                        if connection.in_transaction:
                            connection.rollback()
                        raise

        @staticmethod
        def _canonical_payload(payload: dict[str, Any]) -> str:
            if not isinstance(payload, dict):
                raise TypeError("payload must be an object")
            try:
                return json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                )
            except (TypeError, ValueError) as error:
                raise ValueError(f"payload is not canonical JSON: {error}") from error

        def ingest(self, idempotency_key: str, payload: dict[str, Any]) -> tuple[int, bool]:
            if not isinstance(idempotency_key, str) or not _KEY.fullmatch(idempotency_key):
                raise ValueError("invalid idempotency key")
            encoded = self._canonical_payload(payload)
            if len(encoded.encode("utf-8")) > self.max_payload_bytes:
                raise ValueError("payload exceeds configured byte limit")
            current = self.clock()
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO messages(
                        idempotency_key,payload_json,state,attempt_count,available_at,
                        created_at,updated_at
                    ) VALUES (?,?,'READY',0,?,?,?)
                    """,
                    (idempotency_key, encoded, current, current, current),
                )
                created = cursor.rowcount == 1
                row = connection.execute(
                    "SELECT message_id,payload_json FROM messages WHERE idempotency_key=?",
                    (idempotency_key,),
                ).fetchone()
                assert row is not None
                if row["payload_json"] != encoded:
                    raise ValueError("idempotency key was already used with a different payload")
                connection.commit()
                return int(row["message_id"]), created
            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise
            finally:
                connection.close()

        def _dead_letter(
            self,
            connection: sqlite3.Connection,
            row: sqlite3.Row,
            reason: str,
            current: float,
        ) -> None:
            cursor = connection.execute(
                """
                UPDATE messages
                SET state='DEAD',lease_owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL,last_error=?,dead_lettered_at=?,updated_at=?
                WHERE message_id=? AND state='CLAIMED' AND lease_owner=? AND lease_token=?
                """,
                (
                    reason,
                    current,
                    current,
                    row["message_id"],
                    row["lease_owner"],
                    row["lease_token"],
                ),
            )
            if cursor.rowcount != 1:
                raise LeaseLost("dead-letter transition lost ownership")
            connection.execute(
                """
                INSERT INTO dead_letters(
                    message_id,payload_json,attempts,reason,dead_lettered_at
                ) VALUES (?,?,?,?,?)
                """,
                (
                    row["message_id"],
                    row["payload_json"],
                    row["attempt_count"],
                    reason,
                    current,
                ),
            )

        def _recover_expired(self, connection: sqlite3.Connection, current: float) -> int:
            rows = connection.execute(
                """
                SELECT * FROM messages
                WHERE state='CLAIMED' AND lease_expires_at<=?
                ORDER BY message_id
                """,
                (current,),
            ).fetchall()
            reason = "lease expired before acknowledgement"
            for row in rows:
                if int(row["attempt_count"]) >= self.max_attempts:
                    self._dead_letter(connection, row, reason, current)
                    continue
                cursor = connection.execute(
                    """
                    UPDATE messages
                    SET state='READY',lease_owner=NULL,lease_token=NULL,
                        lease_expires_at=NULL,available_at=?,updated_at=?,last_error=?
                    WHERE message_id=? AND state='CLAIMED'
                          AND lease_owner=? AND lease_token=?
                    """,
                    (
                        current,
                        current,
                        reason,
                        row["message_id"],
                        row["lease_owner"],
                        row["lease_token"],
                    ),
                )
                if cursor.rowcount != 1:
                    raise LeaseLost("expired-lease recovery lost ownership")
            return len(rows)

        def claim(self, owner: str, *, lease_seconds: float = 30.0) -> Delivery | None:
            if not isinstance(owner, str) or not _KEY.fullmatch(owner):
                raise ValueError("invalid owner")
            if lease_seconds <= 0:
                raise ValueError("lease_seconds must be positive")
            current = self.clock()
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                self._recover_expired(connection, current)
                row = connection.execute(
                    """
                    SELECT message_id,idempotency_key,payload_json,attempt_count
                    FROM messages
                    WHERE state IN ('READY','RETRY_WAIT') AND available_at<=?
                    ORDER BY available_at,message_id LIMIT 1
                    """,
                    (current,),
                ).fetchone()
                if row is None:
                    connection.commit()
                    return None
                expires = current + lease_seconds
                token = secrets.token_hex(16)
                cursor = connection.execute(
                    """
                    UPDATE messages
                    SET state='CLAIMED',attempt_count=attempt_count+1,
                        lease_owner=?,lease_token=?,lease_expires_at=?,updated_at=?
                    WHERE message_id=? AND state IN ('READY','RETRY_WAIT')
                          AND available_at<=?
                    """,
                    (owner, token, expires, current, row["message_id"], current),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("atomic claim invariant violated")
                connection.commit()
                return Delivery(
                    int(row["message_id"]),
                    str(row["idempotency_key"]),
                    json.loads(row["payload_json"]),
                    int(row["attempt_count"]) + 1,
                    owner,
                    token,
                    expires,
                )
            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise
            finally:
                connection.close()

        def heartbeat(self, delivery: Delivery, *, lease_seconds: float = 30.0) -> Delivery:
            if lease_seconds <= 0:
                raise ValueError("lease_seconds must be positive")
            current = self.clock()
            requested_expiry = current + lease_seconds
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = self._owned(connection, delivery, current=current)
                expires = max(float(row["lease_expires_at"]), requested_expiry)
                cursor = connection.execute(
                    """
                    UPDATE messages SET lease_expires_at=?,updated_at=?
                    WHERE message_id=? AND state='CLAIMED' AND lease_owner=?
                          AND lease_token=? AND lease_expires_at>?
                    """,
                    (
                        expires,
                        current,
                        delivery.message_id,
                        delivery.lease_owner,
                        delivery.lease_token,
                        current,
                    ),
                )
                if cursor.rowcount != 1:
                    raise LeaseLost("cannot heartbeat an expired or foreign lease")
                connection.commit()
            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise
            finally:
                connection.close()
            return Delivery(
                delivery.message_id,
                delivery.idempotency_key,
                delivery.payload,
                delivery.attempt,
                delivery.lease_owner,
                delivery.lease_token,
                expires,
            )

        def _owned(
            self,
            connection: sqlite3.Connection,
            delivery: Delivery,
            *,
            current: float | None = None,
        ) -> sqlite3.Row:
            observed_at = self.clock() if current is None else current
            row = connection.execute(
                "SELECT * FROM messages WHERE message_id=?",
                (delivery.message_id,),
            ).fetchone()
            if (
                row is None
                or row["state"] != "CLAIMED"
                or row["lease_owner"] != delivery.lease_owner
                or row["lease_token"] != delivery.lease_token
                or float(row["lease_expires_at"]) <= observed_at
            ):
                raise LeaseLost("delivery lease is absent, expired, or foreign")
            return row

        def apply_effect(
            self,
            delivery: Delivery,
            result: dict[str, Any] | None = None,
            *,
            fault: str | None = None,
        ) -> bool:
            if fault == "before_side_effect":
                raise InjectedCrash("crash before side effect")
            encoded = self._canonical_payload(result or {"accepted": True})
            current = self.clock()
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                self._owned(connection, delivery, current=current)
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO effects(message_id,effect_key,result_json,applied_at)
                    VALUES (?,?,?,?)
                    """,
                    (
                        delivery.message_id,
                        f"effect:{delivery.idempotency_key}",
                        encoded,
                        current,
                    ),
                )
                applied = cursor.rowcount == 1
                connection.commit()
            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise
            finally:
                connection.close()
            if fault == "after_side_effect_before_ack":
                raise InjectedCrash("crash after durable side effect and before acknowledgement")
            return applied

        def acknowledge(self, delivery: Delivery) -> None:
            current = self.clock()
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                self._owned(connection, delivery, current=current)
                cursor = connection.execute(
                    """
                    UPDATE messages
                    SET state='DONE',lease_owner=NULL,lease_token=NULL,
                        lease_expires_at=NULL,updated_at=?
                    WHERE message_id=? AND state='CLAIMED' AND lease_owner=?
                          AND lease_token=?
                    """,
                    (
                        current,
                        delivery.message_id,
                        delivery.lease_owner,
                        delivery.lease_token,
                    ),
                )
                if cursor.rowcount != 1:
                    raise LeaseLost("acknowledgement lost ownership")
                connection.commit()
            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise
            finally:
                connection.close()

        def deliver(
            self,
            delivery: Delivery,
            result: dict[str, Any] | None = None,
            *,
            fault: str | None = None,
        ) -> bool:
            applied = self.apply_effect(delivery, result, fault=fault)
            self.acknowledge(delivery)
            return applied

        def fail(self, delivery: Delivery, error: str) -> str:
            reason = str(error).replace("\x00", "?")[:1_000]
            current = self.clock()
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = self._owned(connection, delivery, current=current)
                attempts = int(row["attempt_count"])
                if attempts >= self.max_attempts:
                    self._dead_letter(connection, row, reason, current)
                    state = "DEAD"
                else:
                    delay = self.base_backoff * (2 ** (attempts - 1))
                    cursor = connection.execute(
                        """
                        UPDATE messages SET state='RETRY_WAIT',available_at=?,
                            lease_owner=NULL,lease_token=NULL,lease_expires_at=NULL,
                            last_error=?,updated_at=?
                        WHERE message_id=? AND state='CLAIMED' AND lease_owner=?
                              AND lease_token=?
                        """,
                        (
                            current + delay,
                            reason,
                            current,
                            delivery.message_id,
                            delivery.lease_owner,
                            delivery.lease_token,
                        ),
                    )
                    if cursor.rowcount != 1:
                        raise LeaseLost("retry transition lost ownership")
                    state = "RETRY_WAIT"
                connection.commit()
                return state
            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise
            finally:
                connection.close()

        def release(self, delivery: Delivery) -> None:
            """Gracefully return prefetched work without pretending it succeeded."""

            current = self.clock()
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                self._owned(connection, delivery, current=current)
                cursor = connection.execute(
                    """
                    UPDATE messages SET state='READY',available_at=?,lease_owner=NULL,
                        lease_token=NULL,lease_expires_at=NULL,updated_at=?
                    WHERE message_id=? AND state='CLAIMED' AND lease_owner=?
                          AND lease_token=?
                    """,
                    (
                        current,
                        current,
                        delivery.message_id,
                        delivery.lease_owner,
                        delivery.lease_token,
                    ),
                )
                if cursor.rowcount != 1:
                    raise LeaseLost("cannot release foreign work")
                connection.commit()
            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise
            finally:
                connection.close()

        def counts(self) -> dict[str, int]:
            result = {state: 0 for state in _STATES}
            with self._connect() as connection:
                for row in connection.execute(
                    "SELECT state,COUNT(*) AS total FROM messages GROUP BY state"
                ):
                    result[str(row["state"])] = int(row["total"])
            return result

        def effect_count(self) -> int:
            with self._connect() as connection:
                row = connection.execute("SELECT COUNT(*) AS total FROM effects").fetchone()
            return int(row["total"])

        def list_messages(self, *, limit: int = 20, after: int = 0) -> dict[str, Any]:
            if not 1 <= limit <= 100:
                raise ValueError("limit must be between 1 and 100")
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT message_id,idempotency_key,state,attempt_count,available_at,
                           lease_owner,lease_expires_at,last_error
                    FROM messages WHERE message_id>? ORDER BY message_id LIMIT ?
                    """,
                    (after, limit + 1),
                ).fetchall()
            page = rows[:limit]
            return {
                "items": [dict(row) for row in page],
                "next_after": int(page[-1]["message_id"]) if len(rows) > limit else None,
            }

        def list_dead_letters(self, *, limit: int = 20, after: int = 0) -> dict[str, Any]:
            if not 1 <= limit <= 100:
                raise ValueError("limit must be between 1 and 100")
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT dead_letter_id,message_id,attempts,reason,
                           dead_lettered_at,requeued_at
                    FROM dead_letters
                    WHERE dead_letter_id>? AND requeued_at IS NULL
                    ORDER BY dead_letter_id LIMIT ?
                    """,
                    (after, limit + 1),
                ).fetchall()
            page = rows[:limit]
            return {
                "items": [dict(row) for row in page],
                "next_after": int(page[-1]["dead_letter_id"])
                if len(rows) > limit
                else None,
            }

        def requeue_dead_letter(self, message_id: int) -> None:
            current = self.clock()
            connection = self._connect()
            try:
                connection.execute("BEGIN IMMEDIATE")
                cursor = connection.execute(
                    """
                    UPDATE messages SET state='READY',attempt_count=0,available_at=?,
                        last_error=NULL,dead_lettered_at=NULL,updated_at=?
                    WHERE message_id=? AND state='DEAD'
                    """,
                    (current, current, message_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError("active dead letter not found")
                audit = connection.execute(
                    """
                    UPDATE dead_letters SET requeued_at=?
                    WHERE message_id=? AND requeued_at IS NULL
                    """,
                    (current, message_id),
                )
                if audit.rowcount != 1:
                    raise ValueError("active dead-letter audit row not found")
                connection.commit()
            except BaseException:
                if connection.in_transaction:
                    connection.rollback()
                raise
            finally:
                connection.close()


    class BoundedDispatcher:
        """Claims on demand so queued work never holds an unmaintained lease.

        ``capacity`` remains an API-level memory ceiling for future concurrent
        dispatch, but this deterministic reference keeps at most one outstanding
        delivery. A production prefetcher would need a concurrent lease keeper.
        """

        def __init__(
            self,
            service: EventService,
            owner: str,
            *,
            capacity: int = 8,
            lease_seconds: float = 30.0,
            logger: JsonLogger | None = None,
            metrics: Metrics | None = None,
        ) -> None:
            if capacity < 1:
                raise ValueError("capacity must be positive")
            self.service = service
            self.owner = owner
            self.capacity = capacity
            self.lease_seconds = lease_seconds
            self.logger = logger or JsonLogger()
            self.metrics = metrics or Metrics()
            self._queue: queue.Queue[Delivery] = queue.Queue(maxsize=capacity)
            self._stopping = threading.Event()

        @property
        def buffered(self) -> int:
            return self._queue.qsize()

        def request_stop(self) -> None:
            self._stopping.set()
            self._emit("INFO", "shutdown_requested", owner=self.owner)

        def _emit(self, level: str, event: str, **fields: object) -> None:
            try:
                self.logger.emit(level, event, **fields)
            except Exception:
                # Observability failure after a durable transition must not be
                # misclassified as handler failure or undo queue progress.
                self.metrics.increment("logging_errors_total")

        def fill(self) -> int:
            if self._stopping.is_set() or not self._queue.empty():
                return 0
            delivery = self.service.claim(self.owner, lease_seconds=self.lease_seconds)
            if delivery is None:
                return 0
            self._queue.put_nowait(delivery)
            self.metrics.increment("claimed_total")
            return 1

        def drain_one(self, handler: Callable[[Delivery], dict[str, Any]]) -> bool:
            try:
                delivery = self._queue.get_nowait()
            except queue.Empty:
                return False
            try:
                result = handler(delivery)
                applied = self.service.deliver(delivery, result)
                self.metrics.increment("delivered_total")
                if not applied:
                    self.metrics.increment("duplicate_effect_suppressed_total")
                self._emit(
                    "INFO",
                    "delivery_acknowledged",
                    message_id=delivery.message_id,
                    attempt=delivery.attempt,
                )
            except InjectedCrash:
                raise
            except Exception as error:
                state = self.service.fail(delivery, str(error))
                self.metrics.increment("failed_total")
                if state == "DEAD":
                    self.metrics.increment("dead_lettered_total")
                self._emit(
                    "ERROR",
                    "delivery_failed",
                    message_id=delivery.message_id,
                    state=state,
                    error_type=type(error).__name__,
                )
            finally:
                self._queue.task_done()
            return True

        def run_until_idle(
            self,
            handler: Callable[[Delivery], dict[str, Any]],
            *,
            max_deliveries: int = 10_000,
        ) -> int:
            completed = 0
            while completed < max_deliveries:
                self.fill()
                if not self.drain_one(handler):
                    break
                completed += 1
                # Stop means stop claiming, not discard already-owned work.
                if self._stopping.is_set() and self._queue.empty():
                    break
            return completed

        def release_buffered(self) -> int:
            released = 0
            while True:
                try:
                    delivery = self._queue.get_nowait()
                except queue.Empty:
                    return released
                try:
                    self.service.release(delivery)
                    released += 1
                finally:
                    self._queue.task_done()


    def _main(argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(description="local event queue administration")
        parser.add_argument("--db", required=True)
        commands = parser.add_subparsers(dest="command", required=True)
        ingest = commands.add_parser("ingest")
        ingest.add_argument("key")
        ingest.add_argument("payload_json")
        listing = commands.add_parser("list")
        listing.add_argument("--limit", type=int, default=20)
        listing.add_argument("--after", type=int, default=0)
        commands.add_parser("counts")
        dead = commands.add_parser("dead")
        dead.add_argument("--limit", type=int, default=20)
        dead.add_argument("--after", type=int, default=0)
        requeue = commands.add_parser("requeue")
        requeue.add_argument("message_id", type=int)
        arguments = parser.parse_args(argv)
        service = EventService(arguments.db)
        if arguments.command == "ingest":
            message_id, created = service.ingest(
                arguments.key, json.loads(arguments.payload_json)
            )
            output: object = {"message_id": message_id, "created": created}
        elif arguments.command == "list":
            output = service.list_messages(limit=arguments.limit, after=arguments.after)
        elif arguments.command == "counts":
            output = service.counts()
        elif arguments.command == "dead":
            output = service.list_dead_letters(
                limit=arguments.limit, after=arguments.after
            )
        else:
            service.requeue_dead_letter(arguments.message_id)
            output = {"requeued": arguments.message_id}
        print(json.dumps(output, sort_keys=True))
        return 0


    if __name__ == "__main__":
        raise SystemExit(_main())
'''


_STARTER = r'''
    """Learner starter for a durable event-processing service.

    Implement this API using only Python 3.11 and SQLite. Read REQUIREMENTS.md before
    changing signatures. The sealed implementation is deliberately not imported here.
    """

    from __future__ import annotations

    from dataclasses import dataclass
    from pathlib import Path
    from typing import Any, Callable
    import time


    class LeaseLost(RuntimeError):
        pass


    class InjectedCrash(RuntimeError):
        pass


    @dataclass(frozen=True)
    class Delivery:
        message_id: int
        idempotency_key: str
        payload: dict[str, Any]
        attempt: int
        lease_owner: str
        lease_token: str
        lease_expires_at: float


    class EventService:
        def __init__(
            self,
            path: str | Path,
            *,
            clock: Callable[[], float] = time.time,
            max_attempts: int = 3,
            base_backoff: float = 1.0,
            max_payload_bytes: int = 65_536,
        ) -> None:
            raise NotImplementedError("design the schema and migration runner first")

        def ingest(self, idempotency_key: str, payload: dict[str, Any]) -> tuple[int, bool]:
            raise NotImplementedError

        def claim(self, owner: str, *, lease_seconds: float = 30.0) -> Delivery | None:
            raise NotImplementedError

        def heartbeat(self, delivery: Delivery, *, lease_seconds: float = 30.0) -> Delivery:
            raise NotImplementedError

        def deliver(
            self,
            delivery: Delivery,
            result: dict[str, Any] | None = None,
            *,
            fault: str | None = None,
        ) -> bool:
            raise NotImplementedError

        def fail(self, delivery: Delivery, error: str) -> str:
            raise NotImplementedError

        def counts(self) -> dict[str, int]:
            raise NotImplementedError
'''


_PUBLIC_TESTS = r'''
    import tempfile
    import unittest
    from pathlib import Path

    from event_service import EventService


    class Clock:
        def __init__(self) -> None:
            self.value = 100.0

        def __call__(self) -> float:
            return self.value

        def advance(self, seconds: float) -> None:
            self.value += seconds


    class PublicContractTests(unittest.TestCase):
        def setUp(self) -> None:
            temporary = tempfile.TemporaryDirectory(prefix="event-service-public-")
            self.addCleanup(temporary.cleanup)
            self.path = Path(temporary.name) / "events.db"
            self.clock = Clock()
            self.service = EventService(
                self.path, clock=self.clock, max_attempts=3, base_backoff=2.0
            )

        def test_ingest_is_idempotent_and_rejects_key_reuse(self) -> None:
            first, created = self.service.ingest("order-17", {"amount": 3})
            second, duplicate_created = self.service.ingest("order-17", {"amount": 3})
            self.assertEqual(first, second)
            self.assertTrue(created)
            self.assertFalse(duplicate_created)
            with self.assertRaises(ValueError):
                self.service.ingest("order-17", {"amount": 99})

        def test_claim_then_ack_is_durable(self) -> None:
            self.service.ingest("a", {"kind": "email"})
            delivery = self.service.claim("worker-a", lease_seconds=5)
            self.assertIsNotNone(delivery)
            assert delivery is not None
            self.assertEqual(1, delivery.attempt)
            self.assertTrue(self.service.deliver(delivery, {"sent": True}))
            self.assertEqual(1, self.service.counts()["DONE"])
            self.assertEqual(1, self.service.effect_count())

        def test_failure_waits_for_exponential_retry(self) -> None:
            self.service.ingest("retry-me", {})
            first = self.service.claim("worker-a")
            assert first is not None
            self.assertEqual("RETRY_WAIT", self.service.fail(first, "temporary"))
            self.assertIsNone(self.service.claim("worker-b"))
            self.clock.advance(2.0)
            second = self.service.claim("worker-b")
            self.assertIsNotNone(second)
            assert second is not None
            self.assertEqual(2, second.attempt)


    if __name__ == "__main__":
        unittest.main()
'''


_HIDDEN_TESTS = r'''
    import json
    import tempfile
    import threading
    import unittest
    from pathlib import Path

    from event_service import (
        BoundedDispatcher,
        EventService,
        InjectedCrash,
        JsonLogger,
        LeaseLost,
        Metrics,
    )


    class Clock:
        def __init__(self) -> None:
            self.value = 1_000.0

        def __call__(self) -> float:
            return self.value

        def advance(self, seconds: float) -> None:
            self.value += seconds


    class WithheldContractTests(unittest.TestCase):
        def setUp(self) -> None:
            temporary = tempfile.TemporaryDirectory(prefix="event-service-hidden-")
            self.addCleanup(temporary.cleanup)
            self.path = Path(temporary.name) / "queue.db"
            self.clock = Clock()
            self.service = EventService(
                self.path, clock=self.clock, max_attempts=3, base_backoff=1.0
            )

        def test_migration_is_restart_safe_and_versioned(self) -> None:
            EventService(self.path, clock=self.clock)
            with self.service._connect() as connection:
                versions = connection.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                ).fetchall()
                message_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(messages)")
                }
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
            self.assertEqual(["001_initial.sql"], [row[0] for row in versions])
            self.assertTrue({"messages", "effects", "dead_letters"} <= tables)
            self.assertIn("lease_token", message_columns)

        def test_concurrent_claim_has_one_winner(self) -> None:
            self.service.ingest("only-once", {})
            barrier = threading.Barrier(6)
            winners = []
            failures = []
            lock = threading.Lock()

            def compete(index: int) -> None:
                try:
                    barrier.wait(timeout=5)
                    delivery = self.service.claim(f"worker-{index}")
                    if delivery is not None:
                        with lock:
                            winners.append(delivery)
                except BaseException as error:
                    with lock:
                        failures.append(error)

            threads = [threading.Thread(target=compete, args=(index,)) for index in range(6)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertEqual([], failures)
            self.assertEqual(1, len(winners))

        def test_expired_lease_recovers_after_process_crash(self) -> None:
            self.service.ingest("recover", {})
            abandoned = self.service.claim("dead-worker", lease_seconds=3)
            assert abandoned is not None
            self.assertIsNone(self.service.claim("healthy-worker"))
            self.clock.advance(3)
            recovered = self.service.claim("healthy-worker")
            assert recovered is not None
            self.assertEqual(abandoned.message_id, recovered.message_id)
            self.assertEqual(2, recovered.attempt)
            with self.assertRaises(LeaseLost):
                self.service.acknowledge(abandoned)

        def test_stale_same_owner_delivery_is_fenced_from_new_claim(self) -> None:
            self.service.ingest("fenced", {})
            stale = self.service.claim("stable-worker", lease_seconds=1)
            assert stale is not None
            self.clock.advance(1)
            current = self.service.claim("stable-worker", lease_seconds=10)
            assert current is not None
            self.assertNotEqual(stale.lease_token, current.lease_token)
            for operation in (
                lambda: self.service.heartbeat(stale),
                lambda: self.service.acknowledge(stale),
                lambda: self.service.fail(stale, "stale failure"),
                lambda: self.service.release(stale),
            ):
                with self.assertRaises(LeaseLost):
                    operation()
            self.assertTrue(self.service.deliver(current, {"winner": True}))

        def test_expired_release_is_rejected(self) -> None:
            self.service.ingest("expired-release", {})
            delivery = self.service.claim("worker", lease_seconds=1)
            assert delivery is not None
            self.clock.advance(1)
            with self.assertRaises(LeaseLost):
                self.service.release(delivery)

        def test_heartbeat_never_shortens_a_live_lease(self) -> None:
            self.service.ingest("heartbeat", {})
            delivery = self.service.claim("worker", lease_seconds=20)
            assert delivery is not None
            self.clock.advance(1)
            refreshed = self.service.heartbeat(delivery, lease_seconds=1)
            self.assertEqual(delivery.lease_expires_at, refreshed.lease_expires_at)

        def test_repeated_crash_expiry_exhausts_attempt_budget(self) -> None:
            service = EventService(
                self.path, clock=self.clock, max_attempts=2, base_backoff=1.0
            )
            service.ingest("crash-loop", {})
            first = service.claim("worker-1", lease_seconds=1)
            assert first is not None
            self.clock.advance(1)
            second = service.claim("worker-2", lease_seconds=1)
            assert second is not None
            self.assertEqual(2, second.attempt)
            self.clock.advance(1)
            self.assertIsNone(service.claim("worker-3", lease_seconds=1))
            self.assertEqual(1, service.counts()["DEAD"])
            dead = service.list_dead_letters()["items"]
            self.assertEqual(2, dead[0]["attempts"])
            self.assertIn("lease expired", dead[0]["reason"])

        def test_crash_after_side_effect_before_ack_does_not_duplicate_effect(self) -> None:
            self.service.ingest("payment-7", {"cents": 500})
            first = self.service.claim("worker-a", lease_seconds=2)
            assert first is not None
            with self.assertRaises(InjectedCrash):
                self.service.deliver(
                    first,
                    {"charged": 500},
                    fault="after_side_effect_before_ack",
                )
            self.assertEqual(1, self.service.effect_count())
            self.assertEqual(1, self.service.counts()["CLAIMED"])
            self.clock.advance(2)
            replay = self.service.claim("worker-b", lease_seconds=2)
            assert replay is not None
            self.assertFalse(self.service.deliver(replay, {"charged": 500}))
            self.assertEqual(1, self.service.effect_count())
            self.assertEqual(1, self.service.counts()["DONE"])

        def test_retry_schedule_and_poison_dead_letter_boundary(self) -> None:
            self.service.ingest("poison", {})
            first = self.service.claim("w")
            assert first is not None
            self.assertEqual("RETRY_WAIT", self.service.fail(first, "one"))
            self.clock.advance(1)
            second = self.service.claim("w")
            assert second is not None
            self.assertEqual("RETRY_WAIT", self.service.fail(second, "two"))
            self.clock.advance(1.99)
            self.assertIsNone(self.service.claim("w"))
            self.clock.advance(0.01)
            third = self.service.claim("w")
            assert third is not None
            self.assertEqual("DEAD", self.service.fail(third, "permanent"))
            page = self.service.list_dead_letters()
            self.assertEqual(1, len(page["items"]))
            self.assertEqual(3, page["items"][0]["attempts"])
            self.service.requeue_dead_letter(third.message_id)
            self.assertEqual(1, self.service.counts()["READY"])
            self.assertEqual([], self.service.list_dead_letters()["items"])

        def test_requeue_preserves_prior_dead_letter_audit_cycle(self) -> None:
            service = EventService(self.path, clock=self.clock, max_attempts=1)
            message_id, _ = service.ingest("repeat-poison", {})
            first = service.claim("worker")
            assert first is not None
            self.assertEqual("DEAD", service.fail(first, "cycle one"))
            service.requeue_dead_letter(message_id)
            second = service.claim("worker")
            assert second is not None
            self.assertEqual("DEAD", service.fail(second, "cycle two"))
            with service._connect() as connection:
                history = connection.execute(
                    """
                    SELECT reason,requeued_at FROM dead_letters
                    WHERE message_id=? ORDER BY dead_letter_id
                    """,
                    (message_id,),
                ).fetchall()
            self.assertEqual(["cycle one", "cycle two"], [row["reason"] for row in history])
            self.assertIsNotNone(history[0]["requeued_at"])
            self.assertIsNone(history[1]["requeued_at"])

        def test_keyset_pagination_never_skips_or_repeats(self) -> None:
            for index in range(7):
                self.service.ingest(f"page-{index}", {"index": index})
            seen = []
            after = 0
            while True:
                page = self.service.list_messages(limit=3, after=after)
                seen.extend(item["message_id"] for item in page["items"])
                if page["next_after"] is None:
                    break
                after = page["next_after"]
            self.assertEqual(sorted(seen), seen)
            self.assertEqual(7, len(set(seen)))

        def test_bounded_prefetch_structured_observability_and_graceful_drain(self) -> None:
            for index in range(3):
                self.service.ingest(f"bounded-{index}", {"index": index})
            records = []
            metrics = Metrics()
            dispatcher = BoundedDispatcher(
                self.service,
                "bounded-worker",
                capacity=2,
                logger=JsonLogger(records.append, self.clock),
                metrics=metrics,
            )
            self.assertEqual(1, dispatcher.fill())
            self.assertEqual(1, dispatcher.buffered)
            self.assertEqual(0, dispatcher.fill())
            dispatcher.request_stop()
            self.assertEqual(0, dispatcher.fill())
            self.assertEqual(1, dispatcher.run_until_idle(lambda delivery: {"ok": True}))
            self.assertEqual(0, dispatcher.buffered)
            self.assertEqual(1, self.service.counts()["DONE"])
            self.assertEqual(2, self.service.counts()["READY"])
            self.assertEqual(1, metrics.snapshot()["delivered_total"])
            decoded = [json.loads(line) for line in records]
            self.assertTrue(all({"ts", "level", "event"} <= set(row) for row in decoded))
            self.assertIn("shutdown_requested", {row["event"] for row in decoded})

        def test_claim_on_demand_survives_slow_sequential_handlers(self) -> None:
            for index in range(3):
                self.service.ingest(f"slow-{index}", {})
            dispatcher = BoundedDispatcher(
                self.service,
                "slow-worker",
                capacity=8,
                lease_seconds=1,
                logger=JsonLogger(lambda line: None, self.clock),
            )

            def handler(delivery):
                self.clock.advance(0.6)
                return {"attempt": delivery.attempt}

            self.assertEqual(3, dispatcher.run_until_idle(handler))
            self.assertEqual(3, self.service.counts()["DONE"])

        def test_logging_sink_failure_cannot_reclassify_committed_delivery(self) -> None:
            self.service.ingest("logging-failure", {})

            def broken_sink(line: str) -> None:
                raise OSError("closed log sink")

            metrics = Metrics()
            dispatcher = BoundedDispatcher(
                self.service,
                "worker",
                logger=JsonLogger(broken_sink, self.clock),
                metrics=metrics,
            )
            self.assertEqual(1, dispatcher.run_until_idle(lambda delivery: {"ok": True}))
            self.assertEqual(1, self.service.counts()["DONE"])
            self.assertEqual(1, metrics.snapshot()["logging_errors_total"])


    if __name__ == "__main__":
        unittest.main()
'''


_SYNTAX_CHECK = r'''
    from pathlib import Path


    def main() -> int:
        failures = []
        for path in sorted(Path(".").rglob("*.py")):
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except (OSError, SyntaxError, UnicodeError) as error:
                failures.append(f"{path}: {error}")
        if failures:
            print("\n".join(failures))
            return 1
        print("all generated Python sources compile")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_BOUNDARY_TOOL = r'''
    from __future__ import annotations

    import argparse
    import shutil
    from pathlib import Path


    ALLOWED = (
        "README.md",
        "REQUIREMENTS.md",
        "CONCEPTS.md",
        "DESIGN_QUESTIONS.md",
        "starter",
        "public_tests",
        "environment/requirements.txt",
    )


    def materialize(source: Path, destination: Path) -> None:
        source = source.resolve()
        destination = destination.resolve()
        if source == destination or source in destination.parents:
            raise ValueError("student view must be outside the challenge pack")
        for relative in ALLOWED:
            current = source / relative
            if current.is_symlink() or (
                current.is_dir() and any(path.is_symlink() for path in current.rglob("*"))
            ):
                raise ValueError(f"learner-safe input contains a symlink: {relative}")
        destination.mkdir(parents=True, exist_ok=False)
        for relative in ALLOWED:
            current = source / relative
            target = destination / relative
            if current.is_dir():
                shutil.copytree(current, target)
            elif current.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current, target)


    def main() -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("destination")
        args = parser.parse_args()
        materialize(Path(__file__).resolve().parents[1], Path(args.destination))
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_BOUNDARY_CHECK = r'''
    import subprocess
    import sys
    import tempfile
    from pathlib import Path


    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="event-student-boundary-") as temporary:
        view = Path(temporary) / "student"
        completed = subprocess.run(
            [sys.executable, str(root / "environment/materialize_student_view.py"), str(view)],
            check=False,
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise SystemExit(completed.stderr)
        forbidden = [
            view / "sealed",
            view / "benchmarks",
            view / "debugging",
            view / "review_exercises",
            view / "production",
        ]
        if any(path.exists() for path in forbidden):
            raise SystemExit("student view leaked a reveal-only path")
        names = {path.name for path in view.rglob("*")}
        if "reference_tests" in names or "EXPECTED_REVIEW.md" in names:
            raise SystemExit("student view leaked withheld filenames")
        print("materialized student view contains only explicit learner-safe inputs")
'''


_FAULT_CHECK = r'''
    import os
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    from event_service import EventService


    class Clock:
        def __init__(self) -> None:
            self.now = 10.0

        def __call__(self) -> float:
            return self.now


    def child(path: Path) -> None:
        clock = Clock()
        service = EventService(path, clock=clock)
        delivery = service.claim("crashing-worker", lease_seconds=1)
        assert delivery is not None
        service.apply_effect(delivery, {"charged": 700})
        # Deliberately skip normal unwinding and acknowledgement. The effect's
        # connection has committed and closed, so this is the lost-ack boundary.
        os._exit(71)


    if len(sys.argv) == 3 and sys.argv[1] == "--child":
        child(Path(sys.argv[2]))

    with tempfile.TemporaryDirectory(prefix="event-fault-") as temporary:
        path = Path(temporary) / "queue.db"
        clock = Clock()
        service = EventService(path, clock=clock)
        service.ingest("charge-1", {"cents": 700})
        crashed = subprocess.run(
            [sys.executable, __file__, "--child", str(path)], check=False
        )
        if crashed.returncode != 71:
            raise SystemExit(f"child exited {crashed.returncode}, expected 71")
        if service.effect_count() != 1 or service.counts()["CLAIMED"] != 1:
            raise SystemExit("crash boundary was not durable")
        clock.now += 1
        replay = service.claim("replacement-worker", lease_seconds=1)
        assert replay is not None
        if service.deliver(replay, {"charged": 700}) is not False:
            raise SystemExit("replay repeated an idempotent side effect")
        if service.effect_count() != 1 or service.counts()["DONE"] != 1:
            raise SystemExit("recovery did not acknowledge exactly one effect")
        print("observed child-process death after durable effect, lost ack, lease recovery, and duplicate suppression")
'''


_STRESS_CHECK = r'''
    import tempfile
    import threading
    from pathlib import Path

    from event_service import EventService


    with tempfile.TemporaryDirectory(prefix="event-stress-") as temporary:
        service = EventService(Path(temporary) / "queue.db")
        barrier = threading.Barrier(6)
        errors = []
        lock = threading.Lock()

        def producer(worker: int) -> None:
            try:
                barrier.wait(timeout=5)
                for index in range(30):
                    service.ingest(f"item-{index}", {"index": index})
            except BaseException as error:
                with lock:
                    errors.append(error)

        threads = [threading.Thread(target=producer, args=(index,)) for index in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        if errors or any(thread.is_alive() for thread in threads):
            raise SystemExit(f"producer stress failed: {errors!r}")
        if sum(service.counts().values()) != 30:
            raise SystemExit("idempotent concurrent ingest created duplicates")

        delivered = []
        errors.clear()

        def consumer(worker: int) -> None:
            try:
                while True:
                    delivery = service.claim(f"consumer-{worker}", lease_seconds=10)
                    if delivery is None:
                        return
                    service.deliver(delivery, {"worker": worker})
                    with lock:
                        delivered.append(delivery.message_id)
            except BaseException as error:
                with lock:
                    errors.append(error)

        consumers = [threading.Thread(target=consumer, args=(index,)) for index in range(4)]
        for thread in consumers:
            thread.start()
        for thread in consumers:
            thread.join(timeout=15)
        if errors or any(thread.is_alive() for thread in consumers):
            raise SystemExit(f"consumer stress failed: {errors!r}")
        if len(delivered) != 30 or len(set(delivered)) != 30:
            raise SystemExit("a message was duplicated or lost")
        if service.effect_count() != 30 or service.counts()["DONE"] != 30:
            raise SystemExit("terminal state disagrees with durable effects")
        print("concurrent idempotent ingest and atomic claims passed")
'''


_MODEL_FUZZ = r'''
    import argparse
    import random
    import sqlite3
    import tempfile
    from pathlib import Path

    from event_service import EventService


    class Clock:
        def __init__(self) -> None:
            self.now = 0.0

        def __call__(self) -> float:
            return self.now


    def check_invariants(service: EventService, expected_keys: set[str]) -> None:
        with service._connect() as connection:
            rows = connection.execute("SELECT * FROM messages ORDER BY message_id").fetchall()
            effects = connection.execute("SELECT message_id FROM effects").fetchall()
            dead = connection.execute(
                "SELECT message_id FROM dead_letters WHERE requeued_at IS NULL"
            ).fetchall()
        if {row["idempotency_key"] for row in rows} != expected_keys:
            raise AssertionError("queue diverged from unique-key model")
        if len({row["message_id"] for row in effects}) != len(effects):
            raise AssertionError("duplicate durable effects")
        for row in rows:
            owned = row["lease_owner"] is not None and row["lease_expires_at"] is not None
            if owned != (row["state"] == "CLAIMED"):
                raise AssertionError("lease columns disagree with state")
        dead_ids = {row["message_id"] for row in dead}
        if dead_ids != {row["message_id"] for row in rows if row["state"] == "DEAD"}:
            raise AssertionError("dead-letter projection diverged")


    def main() -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("--seed", type=int, default=20260830)
        parser.add_argument("--steps", type=int, default=160)
        args = parser.parse_args()
        randomizer = random.Random(args.seed)
        clock = Clock()
        with tempfile.TemporaryDirectory(prefix="event-model-") as temporary:
            service = EventService(
                Path(temporary) / "queue.db",
                clock=clock,
                max_attempts=3,
                base_backoff=0.25,
            )
            expected_keys = set()
            for step in range(args.steps):
                if randomizer.random() < 0.55:
                    key = f"key-{randomizer.randrange(35)}"
                    payload = {"key": key}
                    service.ingest(key, payload)
                    expected_keys.add(key)
                else:
                    delivery = service.claim(f"worker-{step % 4}", lease_seconds=1)
                    if delivery is not None:
                        if randomizer.random() < 0.72:
                            service.deliver(delivery, {"ok": True})
                        else:
                            service.fail(delivery, "modeled transient")
                clock.now += randomizer.choice((0.0, 0.25, 0.5, 1.0))
                check_invariants(service, expected_keys)
            # Advance past every retry and drain to a stable DONE/DEAD state.
            for step in range(500):
                clock.now += 2
                delivery = service.claim(f"drain-{step % 3}", lease_seconds=1)
                if delivery is None:
                    if service.counts()["RETRY_WAIT"] == 0:
                        break
                    continue
                service.deliver(delivery, {"ok": True})
            check_invariants(service, expected_keys)
            counts = service.counts()
            if counts["READY"] or counts["CLAIMED"] or counts["RETRY_WAIT"]:
                raise AssertionError(f"model did not quiesce: {counts}")
            print(f"seed={args.seed} steps={args.steps} keys={len(expected_keys)} counts={counts}")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_BENCHMARK = r'''
    from __future__ import annotations

    import argparse
    import hashlib
    import json
    import platform
    import sqlite3
    import sys
    import tempfile
    import time
    from pathlib import Path

    from event_service import BoundedDispatcher, EventService, JsonLogger


    def sample(messages: int, capacity: int, repetition: int) -> dict[str, object]:
        with tempfile.TemporaryDirectory(prefix="event-benchmark-") as temporary:
            path = Path(temporary) / "queue.db"
            service = EventService(path)
            started = time.perf_counter_ns()
            for index in range(messages):
                service.ingest(
                    f"bench-{repetition}-{capacity}-{index}",
                    {"index": index, "payload": "x" * 48},
                )
            ingested = time.perf_counter_ns()
            dispatcher = BoundedDispatcher(
                service,
                f"bench-worker-{capacity}",
                capacity=capacity,
                logger=JsonLogger(lambda line: None),
            )
            processed = dispatcher.run_until_idle(lambda delivery: {"ok": True})
            finished = time.perf_counter_ns()
            if processed != messages or service.counts()["DONE"] != messages:
                raise RuntimeError("benchmark workload did not complete")
            total_ns = finished - started
            return {
                "capacity": capacity,
                "effective_outstanding_limit": 1,
                "repetition": repetition,
                "messages": messages,
                "ingest_ns": ingested - started,
                "delivery_ns": finished - ingested,
                "total_ns": total_ns,
                "messages_per_second": messages / (total_ns / 1_000_000_000),
                "database_bytes": path.stat().st_size,
            }


    def main() -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("--messages", type=int, default=80)
        parser.add_argument("--repetitions", type=int, default=2)
        parser.add_argument("--output", required=True)
        args = parser.parse_args()
        if not 1 <= args.messages <= 2_000 or not 1 <= args.repetitions <= 10:
            raise SystemExit("benchmark bounds exceeded")
        raw_samples = [
            sample(args.messages, capacity, repetition)
            for capacity in (1, 8)
            for repetition in range(args.repetitions)
        ]
        implementation = Path(__import__("event_service").__file__).resolve()
        document = {
            "schema_version": 1,
            "measured_at_unix_ns": time.time_ns(),
            "hypothesis": (
                "The claim-on-demand reference keeps one outstanding lease, so changing the "
                "configured future capacity should not create a prefetch throughput benefit. "
                "Observed differences are descriptive measurement noise."
            ),
            "parameters": {
                "messages": args.messages,
                "repetitions": args.repetitions,
                "capacities": [1, 8],
                "dispatch_policy": "claim_on_demand_one_outstanding",
                "payload_bytes_approximate": 75,
            },
            "environment": {
                "python": sys.version,
                "platform": platform.platform(),
                "sqlite": sqlite3.sqlite_version,
                "implementation": str(implementation),
                "implementation_sha256": hashlib.sha256(
                    implementation.read_bytes()
                ).hexdigest(),
                "timer": "time.perf_counter_ns",
            },
            "command": list(sys.argv),
            "raw_samples": raw_samples,
            "summary": {
                str(capacity): {
                    "minimum_messages_per_second": min(
                        float(row["messages_per_second"])
                        for row in raw_samples
                        if row["capacity"] == capacity
                    ),
                    "maximum_messages_per_second": max(
                        float(row["messages_per_second"])
                        for row in raw_samples
                        if row["capacity"] == capacity
                    ),
                }
                for capacity in (1, 8)
            },
            "interpretation_boundary": (
                "Bounded local smoke data, not a capacity plan: no remote broker, multi-process "
                "contention, fsync audit, long soak, confidence interval, or production hardware. "
                "Capacity is intentionally inert until a lease-keeper-backed prefetcher exists."
            ),
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary_output = output.with_name(output.name + ".tmp")
        temporary_output.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary_output.replace(output)
        print(json.dumps({"samples": len(raw_samples), "output": str(output)}))
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


_BUG_REGRESSION = r'''
    import tempfile
    from pathlib import Path

    from event_service import EventService


    class Clock:
        def __init__(self) -> None:
            self.now = 50.0

        def __call__(self) -> float:
            return self.now


    with tempfile.TemporaryDirectory(prefix="event-poison-regression-") as temporary:
        clock = Clock()
        service = EventService(
            Path(temporary) / "queue.db",
            clock=clock,
            max_attempts=2,
            base_backoff=1,
        )
        service.ingest("poison", {})
        first = service.claim("worker")
        assert first is not None
        if service.fail(first, "still bad") != "RETRY_WAIT":
            raise SystemExit("first failure should be retryable")
        clock.now += 1
        second = service.claim("worker")
        assert second is not None
        state = service.fail(second, "still bad")
        if state != "DEAD":
            print(f"BUG REPRODUCED: max-attempt message remained {state}")
            # A distinct exit code prevents an unrelated Python crash (normally 1)
            # from masquerading as proof that this exact bug reproduced.
            raise SystemExit(23)
        if service.counts()["DEAD"] != 1 or len(service.list_dead_letters()["items"]) != 1:
            raise SystemExit("dead-letter projection missing")
        print("message moved to dead letter on the configured final attempt")
'''


_UNSAFE_CLAIM = r'''
    """Proposed PR implementation. Review it; do not use it as a reference."""

    import sqlite3
    import threading


    def claim_without_transaction(
        path: str, owner: str, selected: threading.Barrier
    ) -> int | None:
        connection = sqlite3.connect(path, timeout=10, isolation_level=None)
        try:
            row = connection.execute(
                "SELECT message_id FROM messages WHERE state='READY' ORDER BY message_id LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            selected.wait(timeout=5)
            # The update neither shares the SELECT transaction nor checks prior state.
            connection.execute(
                """
                UPDATE messages SET state='CLAIMED',lease_owner=?,lease_token=?,
                    lease_expires_at=999999
                WHERE message_id=?
                """,
                (owner, f"unsafe:{owner}", row[0]),
            )
            return int(row[0])
        except sqlite3.Error:
            # PR rationale: avoid waking callers during transient database incidents.
            return None
        finally:
            connection.close()
'''


_REVIEW_DEMONSTRATION = r'''
    import tempfile
    import threading
    from pathlib import Path

    from event_service import EventService
    from unsafe_claim import claim_without_transaction


    with tempfile.TemporaryDirectory(prefix="event-review-") as temporary:
        path = Path(temporary) / "queue.db"
        service = EventService(path)
        expected, _ = service.ingest("review-target", {})
        selected = threading.Barrier(2)
        results = []
        lock = threading.Lock()

        def run(owner: str) -> None:
            value = claim_without_transaction(str(path), owner, selected)
            with lock:
                results.append(value)

        threads = [threading.Thread(target=run, args=(f"review-{index}",)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        if any(thread.is_alive() for thread in threads):
            raise SystemExit("review reproducer stalled")
        if results != [expected, expected] and sorted(results) != [expected, expected]:
            raise SystemExit(f"expected duplicate ownership, observed {results!r}")
        print("demonstrated two callers returning ownership of one message")
'''


_RUN_ALL = r'''
    from __future__ import annotations

    import os
    import subprocess
    import sys
    from pathlib import Path


    ROOT = Path(__file__).resolve().parents[1]


    def run(
        label: str,
        argv: list[str],
        *,
        pythonpath: str | None = None,
        expected: int = 0,
    ) -> None:
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        if pythonpath is not None:
            environment["PYTHONPATH"] = pythonpath
        print(f"==> {label}", flush=True)
        completed = subprocess.run(argv, cwd=ROOT, env=environment, check=False)
        if completed.returncode != expected:
            raise SystemExit(
                f"{label} exited {completed.returncode}; expected {expected}"
            )


    def main() -> int:
        reference = "sealed/reference"
        production = "production/implementation"
        run("syntax", [sys.executable, "environment/check_python.py"])
        for name, path in (("reference", reference), ("production candidate", production)):
            run(
                f"{name} public tests",
                [sys.executable, "-m", "unittest", "discover", "-s", "public_tests", "-v"],
                pythonpath=path,
            )
            run(
                f"{name} withheld tests",
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "sealed/reference_tests",
                    "-v",
                ],
                pythonpath=path,
            )
        run("student boundary", [sys.executable, "environment/check_boundary.py"])
        run(
            "crash fault",
            [sys.executable, "adversarial/fault-injection/crash_after_effect.py"],
            pythonpath=reference,
        )
        run(
            "concurrency stress",
            [sys.executable, "adversarial/stress/concurrent_workers.py"],
            pythonpath=reference,
        )
        run(
            "deterministic model fuzz",
            [
                sys.executable,
                "adversarial/fuzz/model_fuzz.py",
                "--seed",
                "20260830",
                "--steps",
                "160",
            ],
            pythonpath=reference,
        )
        run(
            "bug reproduction",
            [sys.executable, "debugging/dead-letter-off-by-one/regression.py"],
            pythonpath="debugging/dead-letter-off-by-one/buggy",
            expected=23,
        )
        run(
            "bug reference",
            [sys.executable, "debugging/dead-letter-off-by-one/regression.py"],
            pythonpath=reference,
        )
        run(
            "review reproducer",
            [
                sys.executable,
                "review_exercises/non_atomic_batch_claim/sealed/demonstrate.py",
            ],
            pythonpath="review_exercises/non_atomic_batch_claim/proposed:sealed/reference",
        )
        run(
            "bounded measured benchmark",
            [
                sys.executable,
                "benchmarks/benchmark.py",
                "--messages",
                "80",
                "--repetitions",
                "2",
                "--output",
                "benchmarks/results/smoke.json",
            ],
            pythonpath=reference,
        )
        print("all bounded event-service validation stages behaved as expected")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
'''


def generate_event_service_slice(
    workspace: Path, payload: dict[str, Any], db: Database
) -> SliceResult:
    """Generate a bounded, independently validated event-service challenge pack."""

    if not workspace.is_dir() or workspace.is_symlink():
        raise ValueError("event-service workspace must be an existing real directory")
    provenance = _provenance(db, payload)
    # A generator retry starts from source inputs, never stale measured output.
    benchmark_output = _target(workspace, "benchmarks/results/smoke.json")
    if benchmark_output.exists():
        if not benchmark_output.is_file():
            raise ValueError("benchmark output must be a regular file")
        benchmark_output.unlink()

    _write(
        workspace,
        "README.md",
        """
        # Durable Event Processing Service

        Build and operate a deliberately boring service: accept idempotent events, claim work with
        durable leases, retry transient failures, quarantine poison messages, and expose enough
        state to debug an incident. Python 3.11 and SQLite keep every transaction boundary visible.
        There are no packages to install and no network dependency.

        This challenge is **agent-generated cross-source synthesis**. It was synthesized from the
        learning factory's CSDIY and Build Your Own X topic catalogs; it does not copy a tutorial or
        claim to be an upstream project. See `PROVENANCE.json`.

        ## Progressive path

        1. Read `REQUIREMENTS.md`, `CONCEPTS.md`, and `DESIGN_QUESTIONS.md`.
        2. Work only in `starter/`; run `PYTHONPATH=starter python3 -m unittest discover -s public_tests -v`.
        3. Use `environment/materialize_student_view.py` to create an actual view with no sealed,
           hidden-test, production-candidate, debugging-answer, or review-answer files.
        4. After implementing, reveal `sealed/reference_tests/`, then `sealed/reference/` and its design.
        5. Reproduce the lost-ack crash, concurrency stress, model fuzz, bug hunt, and review PR.
        6. Run the benchmark and interpret its raw samples before reading production gaps.

        ```sh
        # Full controller-owned bounded validation (includes a fresh benchmark)
        python3 scripts/run_all.py

        # Keyset-paginated local administration example
        PYTHONPATH=sealed/reference python3 sealed/reference/event_service.py \
          --db /tmp/event-learning.db ingest demo-1 '{"kind":"email"}'
        PYTHONPATH=sealed/reference python3 sealed/reference/event_service.py \
          --db /tmp/event-learning.db list --limit 20 --after 0
        ```

        Passing the included checks supports `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, and
        `REVIEWED`, always alongside `PARTIAL`. This is explicitly **not production-ready** and no
        validator may claim `PRODUCTIONIZED`. The local effect table demonstrates duplicate
        suppression; it cannot make an arbitrary remote side effect atomic with SQLite.
        """,
    )
    _write(
        workspace,
        "MANIFEST.yaml",
        f"""
        schema_version: 1
        id: "durable-event-processing-service"
        title: "Durable Event Processing Service"
        family: "production-services"
        language: "Python 3.11"
        storage: "SQLite"
        difficulty: 8
        estimated_human_hours: 18
        derivation: {json.dumps(provenance['derivation'])}
        deployment_status: "NOT_PRODUCTION_READY"
        productionized: false
        validation_targets:
          - "BUILDS"
          - "TESTED"
          - "FUZZED"
          - "BENCHMARKED"
          - "REVIEWED"
          - "PARTIAL"
        reveal_boundary:
          learner: ["README.md", "REQUIREMENTS.md", "CONCEPTS.md", "DESIGN_QUESTIONS.md", "starter/", "public_tests/"]
          sealed: ["sealed/", "debugging/*/sealed/", "review_exercises/*/sealed/"]
        """,
    )
    _write(
        workspace,
        "REQUIREMENTS.md",
        """
        # Requirements

        ## Durable data model and migrations

        Use numbered SQL migrations recorded durably. A restart may re-run the migration driver but
        must not reapply an already recorded migration. Enforce states and lease-column consistency
        in the schema. Do not use in-memory process identity as ownership.

        ## Ingest contract

        `ingest(key, payload) -> (message_id, created)` atomically inserts one message. Repeating the
        same key and canonical JSON is a successful duplicate; reusing it for different JSON is an
        error. Limit key shape and encoded payload bytes. No caller assertion is evidence of commit.

        ## Delivery contract

        `claim(owner, lease_seconds)` must use a write transaction and guarded update. At most one
        concurrent caller obtains each lease. Expired leases are recoverable after a dead process.
        Attempts increment on claims, not on ingest. Heartbeats may extend only a live owned lease.

        Delivery is **at least once**. Apply the supplied local effect idempotently, then acknowledge
        in a distinct transaction. A crash after the effect but before ack must cause redelivery and
        suppress a duplicate effect. Document why a remote API needs its own idempotency protocol.

        ## Failure policy

        Transient failures enter `RETRY_WAIT` using `base_backoff * 2^(attempt-1)`. The configured
        final attempt atomically transitions the message and its diagnostic snapshot to `DEAD`.
        An administrator can inspect and explicitly requeue a dead letter; requeue resets attempts
        while preserving the audit row.

        ## Backpressure, lifecycle, and operations

        Claim only when dispatch is ready so queued work never holds an unmaintained lease. Any future
        prefetcher must be strictly bounded and heartbeat every outstanding lease. Shutdown stops new
        claims, drains already-owned work, or explicitly releases it—never silently drops it. Emit
        machine-readable log records and
        monotonic counters. Provide keyset pagination for queue/DLQ inspection and a local admin CLI.
        Never return an unbounded result set or use offset pagination for a mutating queue.

        ## Constraints

        Python 3.11 standard library and SQLite only; no external network. Parameterize SQL. Tests
        must use temporary databases. Preserve explicit `PARTIAL` / `NOT_PRODUCTION_READY` labels.
        """,
    )
    _write(
        workspace,
        "CONCEPTS.md",
        """
        # Concepts

        - **Idempotent ingest** makes a client retry safe by binding one key to one canonical request.
        - **Lease, not lock forever:** durable ownership expires so another process can recover work.
        - **At-least-once gap:** side effect and ack are separate commits; either ordering has a crash gap.
        - **Idempotent consumer:** a unique effect key turns replay into an observable no-op locally.
        - **Transactional outbox/inbox:** useful when a database commit is the durable handoff, but not
          magic atomicity across unrelated databases and APIs.
        - **Poison message:** deterministic failure consumes its retry budget and needs quarantine.
        - **Backpressure:** bounded admission transfers overload to the caller instead of growing RAM.
        - **Keyset pagination:** a stable last-seen identity behaves better than offsets during mutation.
        - **Operational evidence:** structured events, counters, runbooks, and raw measurements support
          diagnosis; a green unit test alone does not establish production readiness.
        """,
    )
    _write(
        workspace,
        "DESIGN_QUESTIONS.md",
        """
        # Design questions

        1. Which invariants belong in SQLite constraints, and which require a transaction?
        2. Exactly where can a worker die between claim, side effect, and ack? Draw every resulting state.
        3. If the side effect is an email provider, who owns the idempotency key and retention window?
        4. Should attempt count increase on lease expiry, explicit failure, or both? Defend the policy.
        5. How do clock skew and process pauses affect leases? What would a database-authoritative clock buy?
        6. What should graceful shutdown do when a prefetched lease has too little time left to finish?
        7. Which metrics distinguish a poison burst, database contention, and downstream slowness?
        8. How would online schema migration and rollback work with old and new workers running together?
        9. What information is safe in DLQ payloads and logs? Define redaction and retention policies.
        10. At what scale would you replace or partition SQLite, and what evidence triggers that decision?
        """,
    )
    _write(
        workspace,
        "AGENTS.md",
        """
        # Learner workspace policy

        Implement only from learner-visible requirements and public tests. Do not mount or search
        `sealed/`, debugging answers, or expected reviews while attempting the exercise. Use temporary
        databases, argv-style commands, parameterized SQL, and no network. Preserve failed experiments
        in a concise debugging log; a statement that tests passed is not evaluation evidence.
        """,
    )
    _write_json(
        workspace,
        "PROVENANCE.json",
        {
            "schema_version": 1,
            "derivation": "agent-generated cross-source synthesis",
            "catalog_context": provenance,
            "content_boundary": {
                "source_derived": "catalog topic relationships and provenance metadata only",
                "agent_generated": "all requirements, code, tests, exercises, and prose in this pack",
                "measured": "benchmarks/results/smoke.json only after benchmark execution",
                "inferred": "difficulty, sequencing, and production relevance",
            },
            "tutorial_code_copied": False,
            "external_dependencies": [],
            "network_used_during_generation": False,
        },
    )
    _write_json(
        workspace,
        "CATALOG_ENTRY.json",
        {
            "schema_version": 1,
            "id": "durable-event-processing-service",
            "name": "Durable Event Processing Service",
            "family": "production-services",
            "type": "deep-challenge-pack",
            "languages": ["Python 3.11", "SQL"],
            "concepts": [
                "migrations",
                "idempotency",
                "durable leases",
                "at-least-once delivery",
                "retry backoff",
                "dead letters",
                "crash recovery",
                "backpressure",
                "observability",
                "graceful shutdown",
            ],
            "difficulty": 8,
            "estimated_human_hours": 18,
            "production_relevance": 10,
            "debugging_value": 9,
            "architecture_value": 8,
            "validation_status": ["GENERATED", "PARTIAL"],
            "validation_targets": [
                "BUILDS",
                "TESTED",
                "FUZZED",
                "BENCHMARKED",
                "REVIEWED",
            ],
            "deployment_status": "NOT_PRODUCTION_READY",
            "artifact_paths": {
                "starter": "starter/",
                "reference": "sealed/reference/",
                "hidden_tests": "sealed/reference_tests/",
                "faults": "adversarial/",
                "debugging": "debugging/",
                "review": "review_exercises/",
                "operations": "production/operations/",
            },
            "provenance": "PROVENANCE.json",
        },
    )

    _write(workspace, "starter/event_service.py", _STARTER)
    _write(workspace, "starter/migrations/001_initial.sql", "-- Design this migration before writing service code.\n")
    _write(workspace, "public_tests/test_public_contract.py", _PUBLIC_TESTS)
    _write(workspace, "sealed/reference/event_service.py", _EVENT_SERVICE)
    _write(workspace, "sealed/reference/migrations/001_initial.sql", _MIGRATION)
    _write(workspace, "sealed/reference_tests/test_withheld_contract.py", _HIDDEN_TESTS)
    _write(
        workspace,
        "sealed/DESIGN.md",
        """
        # Reference design

        `BEGIN IMMEDIATE` serializes the choose-and-claim transaction. A guarded update makes the
        ownership assertion explicit. Every terminal transition clears lease columns, reinforced by
        a table check constraint. Ingest binds a unique key to canonical JSON inside one transaction.

        The effect and acknowledgement intentionally use separate transactions. The unique
        `effects.message_id` constraint is the consumer idempotency fence. The injected crash after
        the effect demonstrates why replay is expected, not exceptional. Retry time is persisted so
        restart does not reset it. DLQ insertion shares the terminal transition transaction.

        `BoundedDispatcher` is intentionally single-process and claim-on-demand. It holds at most one
        lease because safe prefetch requires a concurrent lease keeper included in shutdown design.
        """,
    )
    _write(
        workspace,
        "sealed/TRADEOFFS.md",
        """
        # Tradeoffs

        SQLite provides a crisp transactional laboratory and durable single-host queue, but writers
        serialize. `journal_mode=DELETE` favors broad filesystem compatibility over WAL concurrency.
        Application-clock leases are testable yet vulnerable to wall-clock anomalies. Releasing
        owned work improves shutdown latency but can reorder deliveries. Resetting attempts on
        explicit DLQ requeue gives operators a fresh budget while retaining a separate audit record.
        These are choices to debate, not universal defaults.
        """,
    )
    _write(
        workspace,
        "sealed/REVIEW.md",
        """
        # Reference review

        The bounded implementation demonstrates its stated invariants and passes deterministic local
        validation. It deliberately lacks authentication, authorization, encryption, privacy controls,
        disk-capacity safeguards, multi-process soak evidence, online migration compatibility, remote
        side-effect integration, alert wiring, backup/restore drills, and service supervision. Treat it
        as a reference exercise, not deployable service software.
        """,
    )

    # A second independently selected import root represents the instrumented production candidate.
    # It intentionally remains PARTIAL; validating the same invariants is useful without overstating it.
    _write(workspace, "production/implementation/event_service.py", _EVENT_SERVICE)
    _write(workspace, "production/implementation/migrations/001_initial.sql", _MIGRATION)
    _write(
        workspace,
        "production/PRODUCTIONIZATION.md",
        """
        # Productionization review — PARTIAL

        This candidate is **not a production-ready event service**. It is the validated local baseline
        under `production/implementation/`, retained so future work can evolve behind the same tests.
        The correct label is `PARTIAL`, never `PRODUCTIONIZED`.

        Before shipment, add an authenticated ingress/admin boundary; tenant quotas; secret and PII
        handling; log redaction; an external metrics exporter and alerts; disk/inode monitoring;
        backup, restore, and corruption drills; online expand/migrate/contract compatibility; process
        supervision; multi-process and long-soak testing; downstream timeouts/circuit breaking; an
        explicit remote idempotency agreement; load shedding; SLOs; capacity evidence; dependency and
        platform patch policy; and a security/threat review. Decide whether SQLite's serialized writer
        is acceptable from measured peak and recovery demand, not fashion.
        """,
    )
    _write(
        workspace,
        "production/operations/RUNBOOK.md",
        """
        # Operator runbook

        1. Check process health, filesystem free bytes/inodes, SQLite errors, queue counts, oldest
           READY age, retry rate, lease-expiry rate, and DLQ growth.
        2. If backlog grows, first distinguish ingress surge, database contention, and slow downstream.
           Do not raise worker concurrency blindly: SQLite writers serialize and downstream may worsen.
        3. For a poison spike, sample redacted error classes and message types; pause/reject the faulty
           producer if authorized; quarantine rather than infinite retry.
        4. For shutdown, stop ingress/claims, drain within the termination budget, release owned
           work, verify no owned leases remain, then stop. Recovery waits for any abandoned lease.
        5. Requeue DLQ entries only after correcting the root cause and recording operator/change IDs.
        """,
    )
    _write(
        workspace,
        "production/operations/INCIDENTS.md",
        """
        # Incident scenarios

        - **Crash after charge, before ack:** expect lease expiry and replay; verify provider/local
          idempotency key suppressed a second charge before acknowledging.
        - **Database locked:** preserve the first error, inspect transaction duration and competing
          writers, reduce pressure, and avoid deleting lock/journal files.
        - **Disk full:** stop admission, retain the database and journal, create space outside the data
          path, then integrity-check and restore from a tested backup if needed.
        - **DLQ surge:** group by redacted error and schema version, halt the bad producer if safe, fix,
          canary a small requeue, and watch repeat failures.
        - **Lease-expiry surge:** investigate pauses, clock changes, slow handlers, and lease sizing;
          never interpret redelivery alone as duplicate side effects.
        """,
    )
    _write(
        workspace,
        "production/operations/ROLLBACK.md",
        """
        # Deployment and migration rollback

        Use expand/migrate/contract. Deploy readers tolerant of both schemas, apply additive migration,
        deploy writers, backfill with checkpoints, then contract only after old binaries are gone.
        Roll application code back only while its schema compatibility is proven. Do not reverse a
        destructive migration in place during an incident: restore a verified snapshot to a new path,
        validate integrity and queue counts, reconcile external effects with idempotency keys, then
        switch traffic under an explicit change record.
        """,
    )

    _write(workspace, "environment/requirements.txt", "# Python 3.11 standard library only.\n")
    _write(workspace, "environment/check_python.py", _SYNTAX_CHECK)
    _write(workspace, "environment/materialize_student_view.py", _BOUNDARY_TOOL)
    _write(workspace, "environment/check_boundary.py", _BOUNDARY_CHECK)
    _write(
        workspace,
        "environment/README.md",
        """
        # Environment

        Requires Python 3.11 with SQLite enabled. No network or third-party package is used. All test,
        fuzz, stress, and benchmark databases live in temporary directories. The materializer copies
        an explicit allowlist to a destination outside this pack, creating a structural learner view.
        """,
    )

    _write(workspace, "adversarial/fault-injection/crash_after_effect.py", _FAULT_CHECK)
    _write(workspace, "adversarial/stress/concurrent_workers.py", _STRESS_CHECK)
    _write(workspace, "adversarial/fuzz/model_fuzz.py", _MODEL_FUZZ)
    _write(
        workspace,
        "adversarial/README.md",
        """
        # Adversarial validation

        `fault-injection/` crosses the durable side-effect/lost-ack boundary. `stress/` races duplicate
        producers and consumers. `fuzz/` uses a fixed-seed operation model and checks state, ownership,
        uniqueness, and DLQ projection after every step. These are bounded probes, not soak evidence.
        """,
    )

    correct = dedent(_EVENT_SERVICE).lstrip("\n")
    buggy = correct.replace(
        "if attempts >= self.max_attempts:",
        "if attempts > self.max_attempts:",
        1,
    )
    if buggy == correct:
        raise RuntimeError("failed to construct the intentional debugging variant")
    _write(workspace, "debugging/dead-letter-off-by-one/buggy/event_service.py", buggy)
    _write(workspace, "debugging/dead-letter-off-by-one/buggy/migrations/001_initial.sql", _MIGRATION)
    _write(workspace, "debugging/dead-letter-off-by-one/regression.py", _BUG_REGRESSION)
    _write(
        workspace,
        "debugging/dead-letter-off-by-one/README.md",
        """
        # Debugging challenge: poison message never dies on schedule

        With `max_attempts=2`, the second failed delivery should enter the DLQ. The buggy service grants
        another retry. Reproduce with `PYTHONPATH=buggy python3 regression.py`. Find one root cause,
        explain the operational harm, write a regression, and propose safe handling of messages already
        over budget. Reveal `sealed/` only afterward.
        """,
    )
    patch = "".join(
        unified_diff(
            buggy.splitlines(keepends=True),
            correct.splitlines(keepends=True),
            fromfile="a/debugging/dead-letter-off-by-one/buggy/event_service.py",
            tofile="b/debugging/dead-letter-off-by-one/buggy/event_service.py",
        )
    )
    _write(workspace, "debugging/dead-letter-off-by-one/sealed/patch.diff", patch)
    _write(
        workspace,
        "debugging/dead-letter-off-by-one/sealed/root-cause.md",
        """
        # Root cause

        The poison boundary compared `attempts > max_attempts`. Because attempt count already includes
        the active claim, equality is the final permitted attempt and must dead-letter. The off-by-one
        adds work and downstream load to every deterministic poison message. Change the comparison to
        `>=`; the regression proves buggy failure and reference recovery.
        """,
    )
    _write(
        workspace,
        "debugging/dead-letter-off-by-one/sealed/investigation.md",
        """
        # Investigation

        Reproduce with a manual clock, inspect persisted `attempt_count`, and map it to when increments
        occur. Query the message and DLQ in the same observation. Avoid changing backoff or test timing:
        the invariant fails immediately at the second explicit failure. After patching, test attempt 1,
        equality at attempt 2, explicit DLQ requeue, and restart persistence.
        """,
    )

    _write(
        workspace,
        "review_exercises/non_atomic_batch_claim/README.md",
        """
        # Review PR: reduce queue claim latency

        The proposed PR selects READY work before opening a write transaction, updates afterward, and
        catches database errors to reduce caller noise. Write `REVIEW.md` with severity, concrete race
        schedule, operational consequences, required changes, and tests. Look beyond the headline
        throughput rationale. Run the sealed demonstration only after submitting your review.
        """,
    )
    _write(
        workspace,
        "review_exercises/non_atomic_batch_claim/proposed/unsafe_claim.py",
        _UNSAFE_CLAIM,
    )
    _write(
        workspace,
        "review_exercises/non_atomic_batch_claim/PR_DESCRIPTION.md",
        """
        # PR: claim without holding the writer lock during selection

        Moves the initial SELECT outside a write transaction so many workers can discover jobs in
        parallel. Database exceptions return an empty result so transient contention does not wake the
        worker supervisor. The API remains `message_id | None` and no migration is required.
        """,
    )
    _write(
        workspace,
        "review_exercises/non_atomic_batch_claim/sealed/demonstrate.py",
        _REVIEW_DEMONSTRATION,
    )
    _write(
        workspace,
        "review_exercises/non_atomic_batch_claim/sealed/EXPECTED_REVIEW.md",
        """
        # Expected review

        **Blocker:** SELECT and UPDATE are not one claim transaction, and UPDATE has no `state='READY'`
        guard. Two workers select one row, then both update and return ownership. That violates the core
        lease invariant and permits concurrent side effects. Use `BEGIN IMMEDIATE`, select, and guarded
        update with an asserted row count (or a single supported atomic statement).

        **High:** returning `None` for every `sqlite3.Error` makes database outage indistinguishable from
        an empty queue. The worker will look healthy while backlog grows. Surface a typed failure, emit
        structured evidence, and apply bounded infrastructure retry outside claim semantics.

        **High:** the hard-coded lease timestamp is not a duration from an authoritative/injected clock,
        so it may already be expired or effectively permanent. Validate owner/duration and persist an
        actual expiry. Also increment attempts and update audit timestamps in the same transaction.

        Required tests: barrier-forced duplicate selection, guarded row-count loss, lock error visibility,
        lease expiry/recovery, invalid owner, and rollback after injected update failure.
        """,
    )

    _write(workspace, "benchmarks/benchmark.py", _BENCHMARK)
    _write(
        workspace,
        "benchmarks/README.md",
        """
        # Benchmark

        The harness states a hypothesis, captures Python/platform/SQLite/timer/implementation, retains
        every raw repetition, and writes JSON only when executed. It confirms that capacity is an inert
        future ceiling while this safe reference holds one claim at a time. Do not generalize these into a
        capacity plan; add warmup, confidence intervals, multi-process contention, fsync audit, realistic
        payloads, soak duration, and production hardware before making an operational decision.
        """,
    )
    _write(workspace, "scripts/run_all.py", _RUN_ALL)

    validators: list[dict[str, Any]] = [
        {
            "type": "required_paths",
            "name": "event-pack-structure",
            "paths": [
                "README.md",
                "MANIFEST.yaml",
                "PROVENANCE.json",
                "CATALOG_ENTRY.json",
                "REQUIREMENTS.md",
                "starter/event_service.py",
                "public_tests/test_public_contract.py",
                "sealed/reference/event_service.py",
                "sealed/reference/migrations/001_initial.sql",
                "sealed/reference_tests/test_withheld_contract.py",
                "adversarial/fault-injection/crash_after_effect.py",
                "adversarial/stress/concurrent_workers.py",
                "adversarial/fuzz/model_fuzz.py",
                "debugging/dead-letter-off-by-one/buggy/event_service.py",
                "debugging/dead-letter-off-by-one/sealed/patch.diff",
                "review_exercises/non_atomic_batch_claim/sealed/EXPECTED_REVIEW.md",
                "production/PRODUCTIONIZATION.md",
                "production/operations/RUNBOOK.md",
                "production/operations/INCIDENTS.md",
                "production/operations/ROLLBACK.md",
                "benchmarks/benchmark.py",
                "scripts/run_all.py",
            ],
        },
        {
            "type": "json_fields",
            "name": "event-provenance-fields",
            "path": "PROVENANCE.json",
            "required": [
                "schema_version",
                "derivation",
                "catalog_context",
                "content_boundary",
                "tutorial_code_copied",
                "network_used_during_generation",
            ],
        },
        {
            "type": "json_fields",
            "name": "event-catalog-fields",
            "path": "CATALOG_ENTRY.json",
            "required": [
                "schema_version",
                "id",
                "family",
                "languages",
                "concepts",
                "validation_status",
                "validation_targets",
                "deployment_status",
                "artifact_paths",
                "provenance",
            ],
        },
        {
            "type": "command",
            "name": "event-python-syntax",
            "argv": ["python3", "environment/check_python.py"],
            "timeout_seconds": 30,
            "claims": ["BUILDS", "PARTIAL"],
        },
    ]
    for name, python_path in (
        ("reference", "sealed/reference"),
        ("production-candidate", "production/implementation"),
    ):
        validators.extend(
            [
                {
                    "type": "command",
                    "name": f"{name}-public-contract",
                    "argv": [
                        "python3",
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "public_tests",
                        "-v",
                    ],
                    "env": {"PYTHONPATH": python_path},
                    "timeout_seconds": 45,
                    "claims": ["TESTED", "PARTIAL"],
                },
                {
                    "type": "command",
                    "name": f"{name}-withheld-contract",
                    "argv": [
                        "python3",
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "sealed/reference_tests",
                        "-v",
                    ],
                    "env": {"PYTHONPATH": python_path},
                    "timeout_seconds": 60,
                    "claims": ["TESTED", "PARTIAL"],
                },
            ]
        )
    validators.extend(
        [
            {
                "type": "command",
                "name": "student-view-boundary",
                "argv": ["python3", "environment/check_boundary.py"],
                "timeout_seconds": 20,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "crash-after-effect-before-ack",
                "argv": ["python3", "adversarial/fault-injection/crash_after_effect.py"],
                "env": {"PYTHONPATH": "sealed/reference"},
                "timeout_seconds": 30,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "concurrent-ingest-and-claims",
                "argv": ["python3", "adversarial/stress/concurrent_workers.py"],
                "env": {"PYTHONPATH": "sealed/reference"},
                "timeout_seconds": 45,
                "claims": ["TESTED", "FUZZED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "deterministic-queue-model-fuzz",
                "argv": [
                    "python3",
                    "adversarial/fuzz/model_fuzz.py",
                    "--seed",
                    "20260830",
                    "--steps",
                    "160",
                ],
                "env": {"PYTHONPATH": "sealed/reference"},
                "timeout_seconds": 45,
                "claims": ["FUZZED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "dead-letter-bug-reproduces",
                "argv": ["python3", "debugging/dead-letter-off-by-one/regression.py"],
                "env": {"PYTHONPATH": "debugging/dead-letter-off-by-one/buggy"},
                "expected_exit": 23,
                "timeout_seconds": 20,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "dead-letter-reference-repairs",
                "argv": ["python3", "debugging/dead-letter-off-by-one/regression.py"],
                "env": {"PYTHONPATH": "sealed/reference"},
                "timeout_seconds": 20,
                "claims": ["TESTED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "review-race-demonstration",
                "argv": [
                    "python3",
                    "review_exercises/non_atomic_batch_claim/sealed/demonstrate.py",
                ],
                "env": {
                    "PYTHONPATH": "review_exercises/non_atomic_batch_claim/proposed:sealed/reference"
                },
                "timeout_seconds": 20,
                "claims": ["TESTED", "REVIEWED", "PARTIAL"],
            },
            {
                "type": "command",
                "name": "measured-event-service-benchmark",
                "argv": [
                    "python3",
                    "benchmarks/benchmark.py",
                    "--messages",
                    "80",
                    "--repetitions",
                    "2",
                    "--output",
                    "benchmarks/results/smoke.json",
                ],
                "env": {"PYTHONPATH": "sealed/reference"},
                "produces": ["benchmarks/results/smoke.json"],
                "timeout_seconds": 60,
                "claims": ["BENCHMARKED", "PARTIAL"],
            },
            {
                "type": "json_fields",
                "name": "event-benchmark-evidence-fields",
                "path": "benchmarks/results/smoke.json",
                "required": [
                    "schema_version",
                    "measured_at_unix_ns",
                    "hypothesis",
                    "parameters",
                    "environment",
                    "command",
                    "raw_samples",
                    "summary",
                    "interpretation_boundary",
                ],
            },
            {"type": "tree_checksum", "name": "event-pack-tree-checksum"},
        ]
    )

    generated_files = sorted(path for path in workspace.rglob("*") if path.is_file())
    metadata = {
        "name": "Durable Event Processing Service",
        "family": "production-services",
        "type": "deep-challenge-pack",
        "languages": ["Python 3.11", "SQL"],
        "concepts": [
            "migrations",
            "idempotent ingest",
            "durable leases",
            "retry backoff",
            "at-least-once delivery",
            "dead letters",
            "transaction boundaries",
            "crash recovery",
            "bounded queues",
            "observability",
            "graceful shutdown",
            "administration",
        ],
        "difficulty": 8,
        "estimated_human_hours": 18,
        "production_relevance": 10,
        "provenance": provenance,
        "validation_targets": [
            "BUILDS",
            "TESTED",
            "FUZZED",
            "BENCHMARKED",
            "REVIEWED",
            "PARTIAL",
        ],
        "deployment_status": "NOT_PRODUCTION_READY",
        "productionized": False,
        "debugging_challenges": 1,
        "review_exercises": 1,
    }
    pre_validation_tree_sha256 = tree_sha256(workspace)
    evidence = {
        "handler": "generate_event_service_slice",
        "project_id": "durable-event-processing-service",
        "external_validation_required": True,
        "validator_count": len(validators),
        "generated_file_count": len(generated_files),
        "generated_bytes": sum(path.stat().st_size for path in generated_files),
        "candidate_tree_sha256": pre_validation_tree_sha256,
        "pre_validation_tree_sha256": pre_validation_tree_sha256,
        "final_tree_sha256_evidence": "event-pack-tree-checksum validator after benchmark",
        "benchmark_generated_during_validation": True,
        "deployment_status": "NOT_PRODUCTION_READY",
    }
    return SliceResult(
        evidence,
        validators,
        "event_service_challenge_pack",
        "projects/production-services/durable-event-processing-service",
        metadata,
    )
