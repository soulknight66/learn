from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import PureWindowsPath
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urlsplit

from .db import Database
from .util import canonical_json, json_value, new_id, now, redact, tree_sha256
from .workspace import PreparedArtifact


class JobState(str, Enum):
    DISCOVERED = "DISCOVERED"
    READY = "READY"
    CLAIMED = "CLAIMED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    RETRY_WAIT = "RETRY_WAIT"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


ACTIVE_STATES = (JobState.CLAIMED.value, JobState.RUNNING.value)
TERMINAL_STATES = (JobState.SUCCEEDED.value, JobState.FAILED.value, JobState.CANCELLED.value)


@dataclass(frozen=True)
class ClaimedJob:
    job_id: str
    type: str
    worker_type: str
    payload: dict[str, Any]
    attempt_count: int
    workspace: str | None
    model: str | None
    reasoning_effort: str | None
    lease_token: str


class JobError(RuntimeError):
    pass


_JOB_ID_RE = re.compile(r"^job_[A-Za-z0-9][A-Za-z0-9_.-]{0,155}$")
_ENV_NAME_PART_RE = re.compile(r"[A-Z0-9]+")
_DIRECT_CREDENTIAL_NAME_PARTS = frozenset(
    {"TOKEN", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL", "CREDENTIALS"}
)
_NON_VALUE_NAME_SUFFIXES = frozenset(
    {
        "COMMAND",
        "ENABLED",
        "ENDPOINT",
        "ENV",
        "FILE",
        "MODE",
        "NAME",
        "PATH",
        "TYPE",
        "URL",
        "VARIABLE",
    }
)
_NONSECRET_CONTROLLER_VALUES = frozenset(
    {
        "<redacted>",
        "anonymous",
        "changeme",
        "disabled",
        "dummy",
        "example",
        "none",
        "not-a-real-secret",
        "not-a-real-token",
        "not-set",
        "null",
        "placeholder",
        "public",
        "redacted",
        "replace-me",
        "test",
        "testing",
        "unset",
        "your-api-key",
        "your-api-key-here",
        "your-token-here",
    }
)
_MIN_CONTROLLER_CREDENTIAL_LENGTH = 12

SecretValueProvider = Callable[[], Iterable[str]]


def _credential_environment_name(name: str) -> bool:
    """Return whether an environment name conventionally contains a credential value."""
    parts = tuple(_ENV_NAME_PART_RE.findall(name.upper()))
    if not parts:
        return False
    suffix_is_reference = parts[-1] in _NON_VALUE_NAME_SUFFIXES
    has_api_key = "APIKEY" in parts or any(
        first == "API" and second == "KEY"
        for first, second in zip(parts, parts[1:])
    )
    has_direct_credential = bool(_DIRECT_CREDENTIAL_NAME_PARTS.intersection(parts))
    if (has_api_key or has_direct_credential) and not suffix_is_reference:
        return True
    if "AUTHORIZATION" in parts:
        return not suffix_is_reference or parts[-1] == "HEADER"
    if "AUTH" not in parts:
        return False
    return (
        parts[-1] == "AUTH"
        or parts[-1] in {"BEARER", "HEADER", "VALUE"}
        or len(parts) == 1
    )


def _credential_values_from_environment(environment: Mapping[str, str]) -> Iterable[str]:
    """Read values only after their environment-variable name is classified as secret-bearing."""
    for name in environment:
        if not isinstance(name, str) or not _credential_environment_name(name):
            continue
        value = environment.get(name)
        if isinstance(value, str):
            yield value


def _controller_credential_values() -> Iterable[str]:
    return _credential_values_from_environment(os.environ)


def _normalized_controller_credential(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if len(normalized) < _MIN_CONTROLLER_CREDENTIAL_LENGTH:
        return None
    if normalized.casefold() in _NONSECRET_CONTROLLER_VALUES:
        return None
    if normalized.startswith(("/", "./", "../", "~/")):
        return None
    if PureWindowsPath(normalized).drive:
        return None
    try:
        parsed = urlsplit(normalized)
    except ValueError:
        parsed = None
    if (
        parsed is not None
        and parsed.scheme in {"http", "https"}
        and parsed.netloc
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
    ):
        return None
    return normalized


def _reject_controller_credentials(
    serialized_payload: str, secret_value_provider: SecretValueProvider
) -> None:
    """Fail without identifying or reproducing a controller credential."""
    try:
        provided = secret_value_provider()
        values: Iterable[object] = (provided,) if isinstance(provided, str) else provided
        for value in values:
            normalized = _normalized_controller_credential(value)
            if normalized is None:
                continue
            encoded = canonical_json(normalized)
            if encoded[1:-1] in serialized_payload:
                raise JobError("job payload contains a controller credential")
    except JobError:
        raise
    except Exception:
        raise JobError("job payload credential check could not be completed") from None


class JobRepository:
    def __init__(
        self,
        db: Database,
        *,
        retry_base: float = 2,
        retry_max: float = 300,
        secret_value_provider: SecretValueProvider | None = None,
    ):
        self.db = db
        self.retry_base = retry_base
        self.retry_max = retry_max
        self._secret_value_provider = (
            _controller_credential_values
            if secret_value_provider is None
            else secret_value_provider
        )

    def create(
        self,
        job_type: str,
        worker_type: str,
        payload: dict[str, Any],
        *,
        priority: float = 0,
        score_components: dict[str, float] | None = None,
        max_attempts: int = 3,
        dependencies: list[str] | None = None,
        job_id: str | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
    ) -> str:
        identifier = job_id or new_id("job")
        if _JOB_ID_RE.fullmatch(identifier) is None:
            raise JobError(f"invalid job id: {identifier!r}")
        serialized_payload = canonical_json(payload)
        _reject_controller_credentials(serialized_payload, self._secret_value_provider)
        created = now()
        with self.db.transaction(immediate=True) as connection:
            connection.execute(
                """
                INSERT INTO jobs(
                    job_id,type,worker_type,state,priority,score_components_json,payload_json,
                    max_attempts,created_at,model,reasoning_effort
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    identifier,
                    job_type,
                    worker_type,
                    JobState.DISCOVERED.value,
                    priority,
                    canonical_json(score_components or {}),
                    serialized_payload,
                    max_attempts,
                    created,
                    model,
                    reasoning_effort,
                ),
            )
            for dependency in dependencies or []:
                connection.execute(
                    "INSERT INTO job_dependencies(job_id,depends_on_job_id) VALUES (?,?)",
                    (identifier, dependency),
                )
            self.db.emit_event(
                "controller", "JOB_DISCOVERED", job_id=identifier,
                payload={"type": job_type, "worker_type": worker_type, "priority": priority},
                connection=connection,
            )
        return identifier

    def promote_eligible(self, at: float | None = None) -> int:
        promoted = 0
        with self.db.transaction(immediate=True) as connection:
            current = at if at is not None else now()
            ready_rows = connection.execute(
                """
                SELECT j.job_id
                FROM jobs j
                WHERE j.state='DISCOVERED'
                  AND NOT EXISTS (
                    SELECT 1 FROM job_dependencies d
                    JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                    WHERE d.job_id=j.job_id AND parent.state <> 'SUCCEEDED'
                  )
                """
            ).fetchall()
            retry_rows = connection.execute(
                "SELECT job_id FROM jobs WHERE state='RETRY_WAIT' AND retry_at <= ?",
                (current,),
            ).fetchall()
            recovered_dependency_rows = connection.execute(
                """
                SELECT j.job_id
                FROM jobs j
                WHERE j.state='BLOCKED' AND j.failure_kind='blocked_dependency'
                  AND NOT EXISTS (
                    SELECT 1 FROM job_dependencies d
                    JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                    WHERE d.job_id=j.job_id AND parent.state <> 'SUCCEEDED'
                  )
                """
            ).fetchall()
            for row in [*ready_rows, *retry_rows, *recovered_dependency_rows]:
                connection.execute(
                    "UPDATE jobs SET state='READY',retry_at=NULL,error=NULL,failure_kind=NULL WHERE job_id=?",
                    (row["job_id"],),
                )
                self.db.emit_event(
                    "scheduler", "JOB_READY", job_id=row["job_id"], connection=connection
                )
                promoted += 1

            blocked_rows = connection.execute(
                """
                SELECT DISTINCT j.job_id
                FROM jobs j
                JOIN job_dependencies d ON d.job_id=j.job_id
                JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                WHERE j.state='DISCOVERED' AND parent.state IN ('FAILED','CANCELLED','BLOCKED')
                """
            ).fetchall()
            for row in blocked_rows:
                connection.execute(
                    "UPDATE jobs SET state='BLOCKED',error='dependency did not succeed',failure_kind='blocked_dependency' WHERE job_id=?",
                    (row["job_id"],),
                )
                self.db.emit_event(
                    "scheduler", "JOB_BLOCKED_DEPENDENCY", job_id=row["job_id"], connection=connection
                )
        return promoted

    def claim_next(
        self,
        owner: str,
        lease_seconds: float,
        *,
        max_total: int,
        type_limits: dict[str, int],
    ) -> ClaimedJob | None:
        with self.db.transaction(immediate=True) as connection:
            timestamp = now()
            active_total = connection.execute(
                "SELECT COUNT(*) AS n FROM jobs WHERE state IN ('CLAIMED','RUNNING')"
            ).fetchone()["n"]
            if active_total >= max_total:
                return None
            active_by_type = {
                row["worker_type"]: row["n"]
                for row in connection.execute(
                    """
                    SELECT worker_type,COUNT(*) AS n FROM jobs
                    WHERE state IN ('CLAIMED','RUNNING') GROUP BY worker_type
                    """
                )
            }
            candidates = connection.execute(
                """
                SELECT * FROM jobs
                WHERE state='READY' AND cancel_requested=0 AND attempt_count < max_attempts
                ORDER BY priority DESC, created_at ASC, job_id ASC
                """
            ).fetchall()
            selected: sqlite3.Row | None = None
            for candidate in candidates:
                limit = type_limits.get(candidate["worker_type"], max_total)
                if active_by_type.get(candidate["worker_type"], 0) < limit:
                    selected = candidate
                    break
            if selected is None:
                return None
            lease_expires = timestamp + lease_seconds
            lease_token = new_id("lease")
            updated = connection.execute(
                """
                UPDATE jobs
                SET state='CLAIMED',owner=?,lease_token=?,lease_expires_at=?,heartbeat_at=?,
                    attempt_count=attempt_count+1,started_at=COALESCE(started_at,?)
                WHERE job_id=? AND state='READY'
                """,
                (owner, lease_token, lease_expires, timestamp, timestamp, selected["job_id"]),
            )
            if updated.rowcount != 1:
                return None
            row = connection.execute("SELECT * FROM jobs WHERE job_id=?", (selected["job_id"],)).fetchone()
            self.db.emit_event(
                "scheduler", "JOB_CLAIMED", job_id=row["job_id"],
                payload={"owner": owner, "attempt": row["attempt_count"], "lease_expires_at": lease_expires},
                connection=connection,
            )
            return self._claimed(row)

    def start(self, job_id: str, owner: str, lease_token: str, worker_id: str, workspace: str) -> None:
        with self.db.transaction(immediate=True) as connection:
            timestamp = now()
            changed = connection.execute(
                """
                UPDATE jobs SET state='RUNNING',workspace=?,heartbeat_at=?
                WHERE job_id=? AND state='CLAIMED' AND owner=? AND lease_token=?
                  AND cancel_requested=0 AND lease_expires_at >= ?
                """,
                (workspace, timestamp, job_id, owner, lease_token, timestamp),
            )
            if changed.rowcount != 1:
                raise JobError(f"cannot start unowned claim {job_id}")
            self.db.emit_event(
                "worker", "JOB_RUNNING", job_id=job_id, worker_id=worker_id,
                payload={"workspace": workspace}, connection=connection,
            )

    def heartbeat(self, job_id: str, owner: str, lease_token: str, worker_id: str, lease_seconds: float) -> bool:
        with self.db.transaction(immediate=True) as connection:
            timestamp = now()
            changed = connection.execute(
                """
                UPDATE jobs SET heartbeat_at=?,lease_expires_at=?
                WHERE job_id=? AND owner=? AND lease_token=? AND state IN ('CLAIMED','RUNNING')
                  AND cancel_requested=0 AND lease_expires_at >= ?
                """,
                (timestamp, timestamp + lease_seconds, job_id, owner, lease_token, timestamp),
            )
            if changed.rowcount == 1:
                connection.execute(
                    """
                    UPDATE workers SET last_activity=?,state='RUNNING'
                    WHERE worker_id=? AND current_job=? AND state IN ('STARTING','RUNNING')
                    """,
                    (timestamp, worker_id, job_id),
                )
            return changed.rowcount == 1

    def cancellation_requested(self, job_id: str) -> bool:
        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT cancel_requested,state FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
        return bool(row and (row["cancel_requested"] or row["state"] == JobState.CANCELLED.value))

    def succeed(self, job_id: str, owner: str, lease_token: str, worker_id: str) -> None:
        with self.db.transaction(immediate=True) as connection:
            timestamp = now()
            _, summary = self._success_scope(
                connection, job_id, owner, lease_token, timestamp
            )
            self._transition_success(
                connection, job_id, owner, lease_token, worker_id, timestamp, summary["total"]
            )

    def succeed_with_artifact(
        self,
        job_id: str,
        owner: str,
        lease_token: str,
        worker_id: str,
        artifact: PreparedArtifact,
        *,
        on_publish: Callable[[sqlite3.Connection], None] | None = None,
    ) -> None:
        """Atomically publish one artifact, optional state, and its fenced job."""

        if (
            artifact.checksum_algorithm != "tree-sha256-v2"
            or not artifact.path.is_dir()
            or tree_sha256(artifact.path) != artifact.checksum
        ):
            raise JobError("prepared artifact is missing or changed before publication")
        with self.db.transaction(immediate=True) as connection:
            timestamp = now()
            row, summary = self._success_scope(
                connection, job_id, owner, lease_token, timestamp
            )
            if artifact.attempt != row["attempt_count"]:
                raise JobError(
                    f"artifact attempt {artifact.attempt} does not match active attempt {row['attempt_count']}"
                )
            if on_publish is not None:
                on_publish(connection)
            support = [
                {
                    "validation_id": item["validation_id"],
                    "validator": item["validator"],
                    "claims": json_value(item["claims_json"], []),
                }
                for item in connection.execute(
                    """
                    SELECT validation_id,validator,claims_json FROM validations
                    WHERE job_id=? AND attempt_number=? AND status='PASS'
                    ORDER BY started_at,validation_id
                    """,
                    (job_id, artifact.attempt),
                )
            ]
            connection.execute(
                """
                INSERT INTO artifacts(
                    artifact_id,job_id,type,path,checksum,metadata_json,created_at,
                    validation_status,attempt_number,checksum_algorithm,integrity_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    artifact.artifact_id,
                    job_id,
                    artifact.artifact_type,
                    str(artifact.path),
                    artifact.checksum,
                    canonical_json(artifact.metadata),
                    artifact.created_at,
                    artifact.validation_status,
                    artifact.attempt,
                    artifact.checksum_algorithm,
                    "VERIFIED_V2",
                ),
            )
            for label in artifact.validation_labels:
                label_support = [
                    item for item in support
                    if label == "GENERATED" or label in item["claims"]
                ]
                if label != "GENERATED" and not label_support:
                    raise JobError(f"artifact label {label} has no passing validator claim")
                connection.execute(
                    """
                    INSERT INTO artifact_validation_labels(
                        artifact_id,label,evidence_json,created_at
                    ) VALUES (?,?,?,?)
                    """,
                    (
                        artifact.artifact_id,
                        label,
                        canonical_json(
                            {
                                "job_id": job_id,
                                "attempt": artifact.attempt,
                                "support": label_support,
                            }
                        ),
                        timestamp,
                    ),
                )
            self.db.emit_event(
                "archivist", "ARTIFACT_ARCHIVED", job_id=job_id, worker_id=worker_id,
                payload={
                    "artifact_id": artifact.artifact_id,
                    "path": str(artifact.path),
                    "checksum": artifact.checksum,
                    "checksum_algorithm": artifact.checksum_algorithm,
                    "validation_status": artifact.validation_status,
                    "validation_labels": list(artifact.validation_labels),
                    "attempt": artifact.attempt,
                },
                connection=connection,
            )
            self._transition_success(
                connection, job_id, owner, lease_token, worker_id, timestamp, summary["total"]
            )

    def _success_scope(
        self,
        connection: sqlite3.Connection,
        job_id: str,
        owner: str,
        lease_token: str,
        timestamp: float,
    ) -> tuple[sqlite3.Row, sqlite3.Row]:
        row = connection.execute(
            """
            SELECT state,owner,lease_token,lease_expires_at,cancel_requested,attempt_count
            FROM jobs WHERE job_id=?
            """,
            (job_id,),
        ).fetchone()
        if (
            row is None
            or row["state"] != JobState.RUNNING.value
            or row["owner"] != owner
            or row["lease_token"] != lease_token
        ):
            raise JobError(f"cannot succeed unowned running job {job_id}")
        if row["cancel_requested"]:
            raise JobError(f"cannot succeed cancelled job {job_id}")
        if row["lease_expires_at"] is None or row["lease_expires_at"] < timestamp:
            raise JobError(f"cannot succeed job {job_id} with an expired lease")
        summary = connection.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN status='PASS' THEN 1 ELSE 0 END) AS passed,
                   SUM(CASE WHEN status<>'PASS' THEN 1 ELSE 0 END) AS failed
            FROM validations WHERE job_id=? AND attempt_number=?
            """,
            (job_id, row["attempt_count"]),
        ).fetchone()
        if summary["total"] < 1 or summary["failed"]:
            raise JobError(f"job {job_id} cannot succeed without all external validations passing")
        return row, summary

    def _transition_success(
        self,
        connection: sqlite3.Connection,
        job_id: str,
        owner: str,
        lease_token: str,
        worker_id: str,
        timestamp: float,
        validation_count: int,
    ) -> None:
        changed = connection.execute(
            """
            UPDATE jobs SET state='SUCCEEDED',finished_at=?,owner=NULL,lease_expires_at=NULL,
                heartbeat_at=?,error=NULL,failure_kind=NULL,lease_token=NULL
            WHERE job_id=? AND state='RUNNING' AND owner=? AND lease_token=?
              AND cancel_requested=0 AND lease_expires_at >= ?
            """,
            (timestamp, timestamp, job_id, owner, lease_token, timestamp),
        )
        if changed.rowcount != 1:
            raise JobError(f"cannot succeed unowned or cancelled running job {job_id}")
        self.db.emit_event(
            "validator", "JOB_SUCCEEDED", job_id=job_id, worker_id=worker_id,
            payload={"validations": validation_count}, connection=connection,
        )

    def fail(
        self,
        job_id: str,
        owner: str,
        lease_token: str,
        worker_id: str | None,
        *,
        kind: str,
        error: str,
        retryable: bool,
    ) -> JobState:
        safe_error = redact(error)
        with self.db.transaction(immediate=True) as connection:
            timestamp = now()
            row = connection.execute(
                """
                SELECT state,attempt_count,max_attempts,cancel_requested,lease_expires_at
                FROM jobs WHERE job_id=? AND owner=? AND lease_token=?
                """,
                (job_id, owner, lease_token),
            ).fetchone()
            if row is None or row["state"] not in ACTIVE_STATES:
                raise JobError(f"cannot fail unowned active job {job_id}")
            if row["lease_expires_at"] is None or row["lease_expires_at"] < timestamp:
                raise JobError(f"cannot fail job {job_id} with an expired lease")
            cancelled = bool(row["cancel_requested"])
            should_retry = not cancelled and retryable and row["attempt_count"] < row["max_attempts"]
            if cancelled:
                state = JobState.CANCELLED
                retry_at = None
                finished_at = timestamp
            elif should_retry:
                delay = self._retry_delay(job_id, row["attempt_count"])
                state = JobState.RETRY_WAIT
                retry_at = timestamp + delay
                finished_at = None
            else:
                state = JobState.FAILED
                retry_at = None
                finished_at = timestamp
            changed = connection.execute(
                """
                UPDATE jobs SET state=?,retry_at=?,finished_at=?,error=?,failure_kind=?,
                    owner=NULL,lease_token=NULL,lease_expires_at=NULL,heartbeat_at=?
                WHERE job_id=? AND owner=? AND lease_token=?
                  AND state IN ('CLAIMED','RUNNING') AND lease_expires_at >= ?
                """,
                (
                    state.value, retry_at, finished_at, safe_error, kind, timestamp,
                    job_id, owner, lease_token, timestamp,
                ),
            )
            if changed.rowcount != 1:
                raise JobError(f"cannot fail unowned or expired active job {job_id}")
            self.db.emit_event(
                "worker",
                "JOB_CANCELLED" if cancelled else "JOB_RETRY_SCHEDULED" if should_retry else "JOB_FAILED",
                job_id=job_id, worker_id=worker_id,
                payload={"kind": kind, "error": safe_error, "retry_at": retry_at},
                connection=connection,
            )
            return state

    def block(
        self,
        job_id: str,
        owner: str,
        lease_token: str,
        worker_id: str | None,
        *,
        kind: str,
        error: str,
    ) -> None:
        safe_error = redact(error)
        with self.db.transaction(immediate=True) as connection:
            timestamp = now()
            row = connection.execute(
                """
                SELECT state,cancel_requested,lease_expires_at FROM jobs
                WHERE job_id=? AND owner=? AND lease_token=?
                """,
                (job_id, owner, lease_token),
            ).fetchone()
            if row is None or row["state"] != JobState.RUNNING.value:
                raise JobError(f"cannot block unowned running job {job_id}")
            if row["lease_expires_at"] is None or row["lease_expires_at"] < timestamp:
                raise JobError(f"cannot block job {job_id} with an expired lease")
            if row["cancel_requested"]:
                changed = connection.execute(
                    """
                    UPDATE jobs SET state='CANCELLED',finished_at=?,owner=NULL,lease_token=NULL,
                        lease_expires_at=NULL,heartbeat_at=?,error=?,failure_kind='cancelled'
                    WHERE job_id=? AND owner=? AND lease_token=? AND state='RUNNING'
                      AND cancel_requested=1 AND lease_expires_at >= ?
                    """,
                    (timestamp, timestamp, safe_error, job_id, owner, lease_token, timestamp),
                )
                if changed.rowcount != 1:
                    raise JobError(f"cannot cancel unowned or expired running job {job_id}")
                self.db.emit_event(
                    "worker", "JOB_CANCELLED", job_id=job_id, worker_id=worker_id,
                    payload={"during": "block"}, connection=connection,
                )
                return
            changed = connection.execute(
                """
                UPDATE jobs SET state='BLOCKED',owner=NULL,lease_token=NULL,lease_expires_at=NULL,
                    heartbeat_at=?,error=?,failure_kind=?
                WHERE job_id=? AND owner=? AND lease_token=? AND state='RUNNING'
                  AND lease_expires_at >= ?
                """,
                (timestamp, safe_error, kind, job_id, owner, lease_token, timestamp),
            )
            if changed.rowcount != 1:
                raise JobError(f"cannot block unowned running job {job_id}")
            self.db.emit_event(
                "worker", "JOB_BLOCKED", job_id=job_id, worker_id=worker_id,
                payload={"kind": kind, "error": safe_error}, connection=connection,
            )

    def interrupt(
        self,
        job_id: str,
        owner: str,
        lease_token: str,
        worker_id: str,
        *,
        reason: str,
    ) -> None:
        """Persist a controller interruption as resumable work, not cancellation."""

        safe_reason = redact(reason)
        with self.db.transaction(immediate=True) as connection:
            timestamp = now()
            row = connection.execute(
                """
                SELECT state,attempt_count,max_attempts,cancel_requested,lease_expires_at FROM jobs
                WHERE job_id=? AND owner=? AND lease_token=?
                """,
                (job_id, owner, lease_token),
            ).fetchone()
            if row is None or row["state"] not in ACTIVE_STATES:
                raise JobError(f"cannot interrupt unowned active job {job_id}")
            if row["lease_expires_at"] is None or row["lease_expires_at"] < timestamp:
                raise JobError(f"cannot interrupt job {job_id} with an expired lease")
            if row["cancel_requested"]:
                state = JobState.CANCELLED.value
                retry_at = None
                finished_at = timestamp
                max_attempts = row["max_attempts"]
                event = "JOB_CANCELLED"
            else:
                state = JobState.RETRY_WAIT.value
                retry_at = timestamp
                finished_at = None
                max_attempts = max(row["max_attempts"], row["attempt_count"] + 1)
                event = "JOB_INTERRUPTED_FOR_RETRY"
            changed = connection.execute(
                """
                UPDATE jobs SET state=?,retry_at=?,finished_at=?,max_attempts=?,error=?,
                    failure_kind='worker_interrupted',owner=NULL,lease_token=NULL,
                    lease_expires_at=NULL,heartbeat_at=?
                WHERE job_id=? AND owner=? AND lease_token=?
                  AND state IN ('CLAIMED','RUNNING') AND lease_expires_at >= ?
                """,
                (
                    state, retry_at, finished_at, max_attempts, safe_reason,
                    timestamp, job_id, owner, lease_token, timestamp,
                ),
            )
            if changed.rowcount != 1:
                raise JobError(f"cannot interrupt unowned or expired active job {job_id}")
            self.db.emit_event(
                "worker", event, job_id=job_id, worker_id=worker_id,
                payload={"reason": safe_reason, "retry_at": retry_at},
                connection=connection,
            )

    def cancel(self, job_id: str) -> None:
        with self.db.transaction(immediate=True) as connection:
            row = connection.execute("SELECT state FROM jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None:
                raise JobError(f"unknown job {job_id}")
            if row["state"] in ACTIVE_STATES:
                connection.execute("UPDATE jobs SET cancel_requested=1 WHERE job_id=?", (job_id,))
                event = "JOB_CANCEL_REQUESTED"
            elif row["state"] not in TERMINAL_STATES:
                connection.execute(
                    "UPDATE jobs SET state='CANCELLED',cancel_requested=1,finished_at=? WHERE job_id=?",
                    (now(), job_id),
                )
                event = "JOB_CANCELLED"
            else:
                return
            self.db.emit_event("operator", event, job_id=job_id, connection=connection)

    def finish_cancelled(self, job_id: str, owner: str, lease_token: str, worker_id: str) -> None:
        with self.db.transaction(immediate=True) as connection:
            timestamp = now()
            changed = connection.execute(
                """
                UPDATE jobs SET state='CANCELLED',finished_at=?,owner=NULL,lease_token=NULL,lease_expires_at=NULL
                WHERE job_id=? AND owner=? AND lease_token=? AND state IN ('CLAIMED','RUNNING')
                  AND cancel_requested=1 AND lease_expires_at >= ?
                """,
                (timestamp, job_id, owner, lease_token, timestamp),
            )
            if changed.rowcount != 1:
                raise JobError(f"cannot finish unrequested or expired cancellation for {job_id}")
            self.db.emit_event(
                "worker", "JOB_CANCELLED", job_id=job_id, worker_id=worker_id,
                connection=connection,
            )

    def recover_expired(self, at: float | None = None) -> int:
        recovered = 0
        with self.db.transaction(immediate=True) as connection:
            timestamp = at if at is not None else now()
            rows = connection.execute(
                """
                SELECT job_id,attempt_count,max_attempts,state,cancel_requested FROM jobs
                WHERE state IN ('CLAIMED','RUNNING') AND lease_expires_at < ?
                """,
                (timestamp,),
            ).fetchall()
            for row in rows:
                cancelled = bool(row["cancel_requested"])
                retry = not cancelled and row["attempt_count"] < row["max_attempts"]
                state = JobState.CANCELLED if cancelled else JobState.RETRY_WAIT if retry else JobState.FAILED
                retry_at = timestamp + self._retry_delay(row["job_id"], row["attempt_count"]) if retry else None
                connection.execute(
                    """
                    UPDATE jobs SET state=?,owner=NULL,lease_token=NULL,lease_expires_at=NULL,retry_at=?,
                        error='worker lease expired',failure_kind='stall',finished_at=?
                    WHERE job_id=?
                    """,
                    (state.value, retry_at, None if retry else timestamp, row["job_id"]),
                )
                connection.execute(
                    "UPDATE workers SET state='LOST',error='lease expired' WHERE current_job=? AND state IN ('STARTING','RUNNING')",
                    (row["job_id"],),
                )
                self.db.emit_event(
                    "scheduler", "LEASE_EXPIRED", job_id=row["job_id"],
                    payload={
                        "previous_state": row["state"],
                        "next_state": state.value,
                        "cancel_requested": cancelled,
                    },
                    connection=connection,
                )
                recovered += 1
        return recovered

    def retry(self, job_id: str) -> None:
        with self.db.transaction(immediate=True) as connection:
            row = connection.execute(
                "SELECT state,attempt_count,max_attempts FROM jobs WHERE job_id=?",
                (job_id,),
            ).fetchone()
            if row is None or row["state"] not in (JobState.FAILED.value, JobState.BLOCKED.value):
                raise JobError(f"job {job_id} is not retryable from its current state")
            unsatisfied = connection.execute(
                """
                SELECT COUNT(*) AS n FROM job_dependencies d
                JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                WHERE d.job_id=? AND parent.state <> 'SUCCEEDED'
                """,
                (job_id,),
            ).fetchone()["n"]
            if unsatisfied:
                raise JobError(f"job {job_id} still has {unsatisfied} unsatisfied dependencies")
            # Manual retry authorizes one additional attempt without erasing history.
            max_attempts = max(row["max_attempts"], row["attempt_count"] + 1)
            changed = connection.execute(
                """
                UPDATE jobs SET state='READY',retry_at=NULL,error=NULL,failure_kind=NULL,
                    finished_at=NULL,cancel_requested=0,max_attempts=?
                WHERE job_id=? AND state IN ('FAILED','BLOCKED')
                """,
                (max_attempts, job_id),
            )
            if changed.rowcount != 1:
                raise JobError(f"job {job_id} is not retryable from its current state")
            self.db.emit_event(
                "operator", "JOB_MANUALLY_RETRIED", job_id=job_id,
                payload={"previous_state": row["state"], "max_attempts": max_attempts},
                connection=connection,
            )

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self.db.connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["payload"] = json_value(result.pop("payload_json"), {})
        result["score_components"] = json_value(result.pop("score_components_json"), {})
        return result

    @staticmethod
    def _claimed(row: sqlite3.Row) -> ClaimedJob:
        return ClaimedJob(
            job_id=row["job_id"],
            type=row["type"],
            worker_type=row["worker_type"],
            payload=json.loads(row["payload_json"]),
            attempt_count=row["attempt_count"],
            workspace=row["workspace"],
            model=row["model"],
            reasoning_effort=row["reasoning_effort"],
            lease_token=row["lease_token"],
        )

    def _retry_delay(self, job_id: str, attempt: int) -> float:
        raw = hashlib.sha256(f"{job_id}:{attempt}".encode()).digest()
        jitter = 0.75 + int.from_bytes(raw[:2], "big") / 65535 * 0.5
        return min(self.retry_max, self.retry_base * (2 ** max(0, attempt - 1)) * jitter)
