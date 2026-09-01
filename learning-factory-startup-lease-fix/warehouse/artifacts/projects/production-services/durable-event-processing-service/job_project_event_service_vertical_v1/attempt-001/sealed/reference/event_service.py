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
