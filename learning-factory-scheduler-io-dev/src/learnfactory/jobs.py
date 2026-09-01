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
from .publication import (
    PublicationAccessError,
    PublicationConnection,
    PublicationScope,
    restricted_publication_connection,
)
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
_SQLITE_SAFE_DYNAMIC_PARAMETER_COUNT = 900
_CLAIM_CANDIDATE_PAGE_SIZE = 64
_CLAIM_SCAN_MAX_GENERATION_RESTARTS = 8


def _held_by_validator_fence(
    payload_json: str, blocked_validator_types: frozenset[str]
) -> bool:
    """Return whether a READY job must remain unclaimed under a validator fence.

    A malformed validator envelope is held whenever a fence is active. This keeps
    parser disagreement from turning into a bypass while leaving jobs durable and
    otherwise untouched.
    """

    if not blocked_validator_types:
        return False
    try:
        payload = json.loads(payload_json)
    except (TypeError, json.JSONDecodeError):
        return True
    if not isinstance(payload, dict):
        return True
    # Handlers consume only the canonical plural list. Accepting a singular key
    # or mapping here would make the scheduler and worker parse different jobs.
    if "validator" in payload:
        return True
    if "validators" not in payload:
        return False
    specifications = payload["validators"]
    if not isinstance(specifications, list):
        return True
    for spec in specifications:
        if not isinstance(spec, dict):
            return True
        validator_type = spec.get("type")
        if not isinstance(validator_type, str) or not validator_type:
            return True
        if validator_type in blocked_validator_types:
            return True
        if validator_type == "review_acceptance":
            mode = spec.get("mode", "closed")
            if not isinstance(mode, str) or mode not in {"closed", "command"}:
                return True
            if "command" in blocked_validator_types and mode == "command":
                return True
    return False


def _durable_paused(raw: object) -> bool:
    if raw is None:
        return False
    try:
        paused = json.loads(str(raw))
    except (TypeError, json.JSONDecodeError) as error:
        raise JobError("invalid durable paused state") from error
    if not isinstance(paused, bool):
        raise JobError("invalid durable paused state")
    return paused


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


@dataclass(frozen=True)
class _ClaimCandidate:
    job_id: str
    generation: int


class JobError(RuntimeError):
    pass


class PublicationCallbackError(JobError):
    """A deterministic publication callback exceeded its assigned authority."""


class UnsatisfiedDependencyError(JobError):
    """A completion boundary observed a missing or non-successful prerequisite."""


class DependencyPublicationError(UnsatisfiedDependencyError):
    """A publication hook changed dependency edges or their schema guards."""


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
        current = at if at is not None else now()
        # The scheduler calls this on a cadence. Avoid acquiring an NFS write
        # lock when no state transition can occur; the authoritative queries
        # are repeated after BEGIN IMMEDIATE when a candidate does exist.
        with self.db.connect() as connection:
            promotable = connection.execute(
                """
                SELECT (
                  EXISTS(
                    SELECT 1 FROM jobs j
                    WHERE j.state='DISCOVERED'
                      AND NOT EXISTS (
                        SELECT 1 FROM job_dependencies d
                        LEFT JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                        WHERE d.job_id=j.job_id
                          AND (parent.job_id IS NULL OR parent.state <> 'SUCCEEDED')
                      )
                  ) OR EXISTS(
                    SELECT 1 FROM jobs
                    WHERE state='RETRY_WAIT' AND retry_at <= ?
                  ) OR EXISTS(
                    SELECT 1 FROM jobs j
                    WHERE j.state='BLOCKED'
                      AND j.failure_kind='blocked_dependency'
                      AND NOT EXISTS (
                        SELECT 1 FROM job_dependencies d
                        LEFT JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                        WHERE d.job_id=j.job_id
                          AND (parent.job_id IS NULL OR parent.state <> 'SUCCEEDED')
                      )
                  ) OR EXISTS(
                    SELECT 1 FROM jobs j
                    JOIN job_dependencies d ON d.job_id=j.job_id
                    LEFT JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                    WHERE j.state='DISCOVERED'
                      AND (
                        parent.job_id IS NULL
                        OR parent.state IN ('FAILED','CANCELLED','BLOCKED')
                      )
                  )
                ) AS candidate
                """,
                (current,),
            ).fetchone()["candidate"]
        if not promotable:
            return 0
        with self.db.transaction(immediate=True) as connection:
            current = at if at is not None else now()
            ready_rows = connection.execute(
                """
                SELECT j.job_id
                FROM jobs j
                WHERE j.state='DISCOVERED'
                  AND NOT EXISTS (
                    SELECT 1 FROM job_dependencies d
                    LEFT JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                    WHERE d.job_id=j.job_id
                      AND (parent.job_id IS NULL OR parent.state <> 'SUCCEEDED')
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
                    LEFT JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                    WHERE d.job_id=j.job_id
                      AND (parent.job_id IS NULL OR parent.state <> 'SUCCEEDED')
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
                LEFT JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                WHERE j.state='DISCOVERED'
                  AND (
                    parent.job_id IS NULL
                    OR parent.state IN ('FAILED','CANCELLED','BLOCKED')
                  )
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
        blocked_validator_types: frozenset[str] = frozenset(),
    ) -> ClaimedJob | None:
        # Selection reads bounded pages from independently released snapshots.
        # JSON parsing therefore never retains a rollback-journal SHARED lock.
        # A trigger-maintained generation makes the eventual writer reject a
        # candidate if READY order or active capacity changed between phases.
        with self.db.connect() as connection:
            paused_row = connection.execute(
                "SELECT value_json FROM system_state WHERE key='paused'"
            ).fetchone()
            if _durable_paused(
                paused_row["value_json"] if paused_row is not None else None
            ):
                return None
        selected = self._select_claimable_candidate(
            max_total=max_total,
            type_limits=type_limits,
            blocked_validator_types=blocked_validator_types,
        )
        if selected is None:
            return None
        with self.db.transaction(immediate=True) as connection:
            paused_row = connection.execute(
                "SELECT value_json FROM system_state WHERE key='paused'"
            ).fetchone()
            if _durable_paused(
                paused_row["value_json"] if paused_row is not None else None
            ):
                return None
            if self._claim_generation(connection) != selected.generation:
                return None
            active_by_type = self._active_by_type(connection)
            active_total = sum(active_by_type.values())
            if active_total >= max_total:
                return None
            row = connection.execute(
                """
                SELECT candidate.* FROM jobs candidate
                WHERE candidate.job_id=? AND candidate.state='READY'
                  AND candidate.cancel_requested=0
                  AND candidate.attempt_count < candidate.max_attempts
                  AND NOT EXISTS (
                    SELECT 1
                    FROM job_dependencies dependency
                    LEFT JOIN jobs prerequisite
                      ON prerequisite.job_id=dependency.depends_on_job_id
                    WHERE dependency.job_id=candidate.job_id
                      AND (
                        prerequisite.job_id IS NULL
                        OR prerequisite.state <> 'SUCCEEDED'
                      )
                  )
                """,
                (selected.job_id,),
            ).fetchone()
            if row is None:
                return None
            worker_type = str(row["worker_type"])
            if active_by_type.get(worker_type, 0) >= type_limits.get(
                worker_type, max_total
            ):
                return None
            if _held_by_validator_fence(
                row["payload_json"], blocked_validator_types
            ):
                return None
            timestamp = now()
            lease_expires = timestamp + lease_seconds
            lease_token = new_id("lease")
            updated = connection.execute(
                """
                UPDATE jobs
                SET state='CLAIMED',owner=?,lease_token=?,lease_expires_at=?,heartbeat_at=?,
                    attempt_count=attempt_count+1,started_at=COALESCE(started_at,?)
                WHERE job_id=? AND state='READY'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM job_dependencies dependency
                    LEFT JOIN jobs prerequisite
                      ON prerequisite.job_id=dependency.depends_on_job_id
                    WHERE dependency.job_id=jobs.job_id
                      AND (
                        prerequisite.job_id IS NULL
                        OR prerequisite.state <> 'SUCCEEDED'
                      )
                  )
                """,
                (owner, lease_token, lease_expires, timestamp, timestamp, row["job_id"]),
            )
            if updated.rowcount != 1:
                return None
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id=?", (row["job_id"],)
            ).fetchone()
            self.db.emit_event(
                "scheduler", "JOB_CLAIMED", job_id=row["job_id"],
                payload={"owner": owner, "attempt": row["attempt_count"], "lease_expires_at": lease_expires},
                connection=connection,
            )
            return self._claimed(row)

    @staticmethod
    def _active_by_type(connection: sqlite3.Connection) -> dict[str, int]:
        return {
            str(row["worker_type"]): int(row["n"])
            for row in connection.execute(
                """
                SELECT worker_type,COUNT(*) AS n FROM jobs
                WHERE state IN ('CLAIMED','RUNNING') GROUP BY worker_type
                """
            )
        }

    def _select_claimable_candidate(
        self,
        *,
        max_total: int,
        type_limits: Mapping[str, int],
        blocked_validator_types: frozenset[str],
    ) -> _ClaimCandidate | None:
        """Return the canonical claim candidate from released bounded pages.

        Each page is fetched under a short consistent snapshot, then its
        payloads are parsed only after that connection closes. If a scheduling
        mutation occurs between pages, the scan restarts from the beginning.
        The writer later checks the same generation before granting ownership.
        """

        for _restart in range(_CLAIM_SCAN_MAX_GENERATION_RESTARTS):
            generation: int | None = None
            continuation: tuple[float, float, str] | None = None
            saturated_types: set[str] = set()
            restart = False
            while True:
                with self.db.read_transaction() as connection:
                    page_generation = self._claim_generation(connection)
                    if generation is None:
                        generation = page_generation
                        active_by_type = self._active_by_type(connection)
                        if sum(active_by_type.values()) >= max_total:
                            return None
                        saturated_types = {
                            worker_type
                            for worker_type in set(active_by_type) | set(type_limits)
                            if active_by_type.get(worker_type, 0)
                            >= type_limits.get(worker_type, max_total)
                        }
                        if saturated_types and not self._has_unsaturated_ready_type(
                            connection,
                            saturated_types,
                        ):
                            return None
                    elif page_generation != generation:
                        restart = True
                        break
                    candidates = self._claim_candidate_page(
                        connection,
                        continuation=continuation,
                        saturated_types=saturated_types,
                    )

                # The connection and its SHARED lock are gone before any
                # potentially expensive or adversarial payload parsing.
                selected_job_id: str | None = None
                for candidate in candidates:
                    if str(candidate["worker_type"]) in saturated_types:
                        continue
                    if not _held_by_validator_fence(
                        candidate["payload_json"], blocked_validator_types
                    ):
                        selected_job_id = str(candidate["job_id"])
                        break
                if selected_job_id is not None:
                    assert generation is not None
                    with self.db.connect() as connection:
                        generation_after_parse = self._claim_generation(connection)
                    if generation_after_parse != generation:
                        restart = True
                        break
                    return _ClaimCandidate(
                        job_id=selected_job_id,
                        generation=generation,
                    )
                if len(candidates) < _CLAIM_CANDIDATE_PAGE_SIZE:
                    return None
                last = candidates[-1]
                continuation = (
                    float(last["priority_key"]),
                    float(last["created_at"]),
                    str(last["job_id"]),
                )
            if not restart:
                return None
        # Sustained scheduling churn is not an infrastructure failure. Leave
        # the queue untouched and let the next deterministic poll retry.
        return None

    @staticmethod
    def _claim_generation(connection: sqlite3.Connection) -> int:
        try:
            row = connection.execute(
                """
                SELECT generation FROM scheduler_generations
                WHERE name='jobs_claim_projection'
                """
            ).fetchone()
        except sqlite3.OperationalError as error:
            raise JobError(
                "scheduler claim cursor schema is unavailable; run `learnfactory init`"
            ) from error
        if row is None:
            raise JobError("scheduler claim generation row is missing")
        generation = row["generation"]
        if isinstance(generation, bool) or not isinstance(generation, int):
            raise JobError("scheduler claim generation is invalid")
        return generation

    @staticmethod
    def _has_unsaturated_ready_type(
        connection: sqlite3.Connection,
        saturated_types: set[str],
    ) -> bool:
        if len(saturated_types) > _SQLITE_SAFE_DYNAMIC_PARAMETER_COUNT:
            return True
        ordered_types = tuple(sorted(saturated_types))
        placeholders = ",".join("?" for _ in ordered_types)
        return connection.execute(
            f"""
            SELECT 1 FROM jobs candidate
            WHERE candidate.state='READY' AND candidate.cancel_requested=0
              AND candidate.attempt_count < candidate.max_attempts
              AND candidate.worker_type NOT IN ({placeholders})
              AND NOT EXISTS (
                SELECT 1
                FROM job_dependencies dependency
                LEFT JOIN jobs prerequisite
                  ON prerequisite.job_id=dependency.depends_on_job_id
                WHERE dependency.job_id=candidate.job_id
                  AND (
                    prerequisite.job_id IS NULL
                    OR prerequisite.state <> 'SUCCEEDED'
                  )
              )
            LIMIT 1
            """,
            ordered_types,
        ).fetchone() is not None

    @staticmethod
    def _claim_candidate_page(
        connection: sqlite3.Connection,
        *,
        continuation: tuple[float, float, str] | None,
        saturated_types: set[str],
    ) -> list[sqlite3.Row]:
        statement = """
            SELECT job_id,worker_type,payload_json,
                   claim_priority_key AS priority_key,created_at
            FROM jobs candidate
            WHERE candidate.state='READY' AND candidate.cancel_requested=0
              AND candidate.attempt_count < candidate.max_attempts
              AND NOT EXISTS (
                SELECT 1
                FROM job_dependencies dependency
                LEFT JOIN jobs prerequisite
                  ON prerequisite.job_id=dependency.depends_on_job_id
                WHERE dependency.job_id=candidate.job_id
                  AND (
                    prerequisite.job_id IS NULL
                    OR prerequisite.state <> 'SUCCEEDED'
                  )
              )
        """
        parameters: list[object] = []
        if 0 < len(saturated_types) <= _SQLITE_SAFE_DYNAMIC_PARAMETER_COUNT:
            ordered_types = tuple(sorted(saturated_types))
            placeholders = ",".join("?" for _ in ordered_types)
            statement += f" AND worker_type NOT IN ({placeholders})"
            parameters.extend(ordered_types)
        if continuation is not None:
            statement += (
                " AND (claim_priority_key,created_at,job_id) > (?,?,?)"
            )
            parameters.extend(continuation)
        statement += (
            " ORDER BY claim_priority_key,created_at,job_id LIMIT ?"
        )
        parameters.append(_CLAIM_CANDIDATE_PAGE_SIZE)
        return connection.execute(statement, tuple(parameters)).fetchall()

    def count_ready_held_by_validator_fence(
        self, blocked_validator_types: frozenset[str]
    ) -> int:
        if not blocked_validator_types:
            return 0
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM jobs
                WHERE state='READY' AND cancel_requested=0
                  AND attempt_count < max_attempts
                """
            ).fetchall()
        return sum(
            _held_by_validator_fence(row["payload_json"], blocked_validator_types)
            for row in rows
        )

    def count_ready_claimable(
        self,
        blocked_validator_types: frozenset[str],
        *,
        type_limits: Mapping[str, int] | None = None,
    ) -> int:
        with self.db.connect() as connection:
            rows = connection.execute(
                """
                SELECT candidate.worker_type,candidate.payload_json
                FROM jobs candidate
                WHERE candidate.state='READY' AND candidate.cancel_requested=0
                  AND candidate.attempt_count < candidate.max_attempts
                  AND NOT EXISTS (
                    SELECT 1
                    FROM job_dependencies dependency
                    LEFT JOIN jobs prerequisite
                      ON prerequisite.job_id=dependency.depends_on_job_id
                    WHERE dependency.job_id=candidate.job_id
                      AND (
                        prerequisite.job_id IS NULL
                        OR prerequisite.state <> 'SUCCEEDED'
                      )
                  )
                """
            ).fetchall()
        return sum(
            (type_limits is None or type_limits.get(row["worker_type"], 1) > 0)
            and not _held_by_validator_fence(
                row["payload_json"], blocked_validator_types
            )
            for row in rows
        )

    def start(
        self,
        job_id: str,
        owner: str,
        lease_token: str,
        worker_id: str,
        workspace: str,
        *,
        lease_seconds: float,
    ) -> float:
        with self.db.transaction(immediate=True) as connection:
            timestamp = now()
            lease_expires_at = timestamp + lease_seconds
            changed = connection.execute(
                """
                UPDATE jobs SET state='RUNNING',workspace=?,heartbeat_at=?,
                    lease_expires_at=?
                WHERE job_id=? AND state='CLAIMED' AND owner=? AND lease_token=?
                  AND cancel_requested=0 AND lease_expires_at >= ?
                """,
                (
                    workspace,
                    timestamp,
                    lease_expires_at,
                    job_id,
                    owner,
                    lease_token,
                    timestamp,
                ),
            )
            if changed.rowcount != 1:
                raise JobError(f"cannot start unowned claim {job_id}")
            self.db.emit_event(
                "worker", "JOB_RUNNING", job_id=job_id, worker_id=worker_id,
                payload={
                    "workspace": workspace,
                    "lease_expires_at": lease_expires_at,
                },
                connection=connection,
            )
        return lease_expires_at

    def heartbeat(
        self,
        job_id: str,
        owner: str,
        lease_token: str,
        worker_id: str,
        lease_seconds: float,
        busy_timeout_seconds: float | None = None,
    ) -> float | None:
        with self.db.transaction(
            immediate=True,
            busy_timeout_seconds=busy_timeout_seconds,
        ) as connection:
            timestamp = now()
            lease_expires_at = timestamp + lease_seconds
            changed = connection.execute(
                """
                UPDATE jobs SET heartbeat_at=?,lease_expires_at=?
                WHERE job_id=? AND owner=? AND lease_token=? AND state IN ('CLAIMED','RUNNING')
                  AND cancel_requested=0 AND lease_expires_at >= ?
                """,
                (
                    timestamp,
                    lease_expires_at,
                    job_id,
                    owner,
                    lease_token,
                    timestamp,
                ),
            )
            if changed.rowcount == 1:
                connection.execute(
                    """
                    UPDATE workers SET last_activity=?,state='RUNNING'
                    WHERE worker_id=? AND current_job=? AND state IN ('STARTING','RUNNING')
                    """,
                    (timestamp, worker_id, job_id),
                )
            return lease_expires_at if changed.rowcount == 1 else None

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
        on_publish: Callable[[PublicationConnection], None] | None = None,
        publication_scope: PublicationScope | None = None,
    ) -> None:
        """Atomically publish one artifact, optional state, and its fenced job."""

        if (
            artifact.checksum_algorithm != "tree-sha256-v2"
            or not artifact.path.is_dir()
            or tree_sha256(artifact.path) != artifact.checksum
        ):
            raise JobError("prepared artifact is missing or changed before publication")
        if on_publish is not None and publication_scope is None:
            raise JobError("publication callback requires an orchestrator-selected scope")
        if on_publish is None and publication_scope is not None:
            raise JobError("publication scope requires a publication callback")
        with self.db.transaction(immediate=True) as connection:
            timestamp = now()
            row, summary = self._success_scope(
                connection, job_id, owner, lease_token, timestamp
            )
            dependency_snapshot = self._dependency_publication_snapshot(
                connection,
                job_id,
            )
            if artifact.attempt != row["attempt_count"]:
                raise JobError(
                    f"artifact attempt {artifact.attempt} does not match active attempt {row['attempt_count']}"
                )
            if on_publish is not None:
                assert publication_scope is not None
                try:
                    with restricted_publication_connection(
                        connection, publication_scope
                    ) as publication:
                        on_publish(publication)
                except PublicationAccessError as error:
                    raise PublicationCallbackError(
                        f"publication hook exceeded authority for {job_id}: {error}"
                    ) from error
                except sqlite3.IntegrityError as error:
                    if "dependencies may only be" in str(error):
                        raise DependencyPublicationError(
                            f"publication hook changed dependencies for {job_id}"
                        ) from error
                    raise
                self._assert_dependency_publication_snapshot(
                    connection,
                    job_id,
                    dependency_snapshot,
                )
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
        if self._has_unsatisfied_dependencies(connection, job_id):
            raise UnsatisfiedDependencyError(
                f"cannot succeed job {job_id} with unsatisfied dependencies"
            )
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
              AND NOT EXISTS (
                SELECT 1
                FROM job_dependencies dependency
                LEFT JOIN jobs prerequisite
                  ON prerequisite.job_id=dependency.depends_on_job_id
                WHERE dependency.job_id=jobs.job_id
                  AND (
                    prerequisite.job_id IS NULL
                    OR prerequisite.state <> 'SUCCEEDED'
                  )
              )
            """,
            (timestamp, timestamp, job_id, owner, lease_token, timestamp),
        )
        if changed.rowcount != 1:
            if self._has_unsatisfied_dependencies(connection, job_id):
                raise UnsatisfiedDependencyError(
                    f"cannot succeed job {job_id} with unsatisfied dependencies"
                )
            raise JobError(f"cannot succeed unowned or cancelled running job {job_id}")
        self.db.emit_event(
            "validator", "JOB_SUCCEEDED", job_id=job_id, worker_id=worker_id,
            payload={"validations": validation_count}, connection=connection,
        )

    @staticmethod
    def _has_unsatisfied_dependencies(
        connection: sqlite3.Connection,
        job_id: str,
    ) -> bool:
        return connection.execute(
            """
            SELECT 1
            FROM job_dependencies dependency
            LEFT JOIN jobs prerequisite
              ON prerequisite.job_id=dependency.depends_on_job_id
            WHERE dependency.job_id=?
              AND (
                prerequisite.job_id IS NULL
                OR prerequisite.state <> 'SUCCEEDED'
              )
            LIMIT 1
            """,
            (job_id,),
        ).fetchone() is not None

    @staticmethod
    def _dependency_publication_snapshot(
        connection: sqlite3.Connection,
        job_id: str,
    ) -> tuple[
        tuple[tuple[str, str | None], ...],
        tuple[tuple[str, str, str, str | None], ...],
    ]:
        edges = tuple(
            (
                str(row["depends_on_job_id"]),
                str(row["prerequisite_state"])
                if row["prerequisite_state"] is not None
                else None,
            )
            for row in connection.execute(
                """
                SELECT dependency.depends_on_job_id,
                       prerequisite.state AS prerequisite_state
                FROM job_dependencies dependency
                LEFT JOIN jobs prerequisite
                  ON prerequisite.job_id=dependency.depends_on_job_id
                WHERE dependency.job_id=?
                ORDER BY dependency.depends_on_job_id
                """,
                (job_id,),
            )
        )
        schema = tuple(
            (
                str(row["type"]),
                str(row["name"]),
                str(row["tbl_name"]),
                str(row["sql"]) if row["sql"] is not None else None,
            )
            for row in connection.execute(
                """
                SELECT type,name,tbl_name,sql
                FROM sqlite_master
                WHERE tbl_name IN ('jobs','job_dependencies')
                   OR name IN ('jobs','job_dependencies')
                ORDER BY type,name
                """
            )
        )
        return edges, schema

    @classmethod
    def _assert_dependency_publication_snapshot(
        cls,
        connection: sqlite3.Connection,
        job_id: str,
        expected: tuple[
            tuple[tuple[str, str | None], ...],
            tuple[tuple[str, str, str, str | None], ...],
        ],
    ) -> None:
        try:
            observed = cls._dependency_publication_snapshot(connection, job_id)
        except sqlite3.Error as error:
            raise DependencyPublicationError(
                f"publication hook damaged dependency state for {job_id}"
            ) from error
        if observed != expected:
            raise DependencyPublicationError(
                f"publication hook changed dependency state for {job_id}"
            )
        if cls._has_unsatisfied_dependencies(connection, job_id):
            raise UnsatisfiedDependencyError(
                f"cannot succeed job {job_id} with unsatisfied dependencies"
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
    ) -> JobState:
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
            return JobState(state)

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
        timestamp = at if at is not None else now()
        with self.db.connect() as connection:
            expired = connection.execute(
                """
                SELECT 1 FROM jobs
                WHERE state IN ('CLAIMED','RUNNING') AND lease_expires_at < ?
                LIMIT 1
                """,
                (timestamp,),
            ).fetchone()
        if expired is None:
            return 0
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
                LEFT JOIN jobs parent ON parent.job_id=d.depends_on_job_id
                WHERE d.job_id=?
                  AND (parent.job_id IS NULL OR parent.state <> 'SUCCEEDED')
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
