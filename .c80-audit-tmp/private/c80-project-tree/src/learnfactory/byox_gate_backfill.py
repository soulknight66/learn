from __future__ import annotations

import contextlib
import hashlib
import heapq
import json
import math
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence

from .byox_jobs import (
    BYOX_CODE_PRESENCE_VALIDATOR,
    byox_runtime_safety_validators,
)
from .db import Database
from .util import canonical_json, now
from .validation import (
    BYOX_TREE_MAX_DEPTH,
    ByoxCodeManifest,
    ByoxCodeManifestEntry,
    byox_code_manifest_digest,
    byox_code_policy_manifest_digest,
    byox_code_manifest_tree_sha256,
    byox_code_policy_digest,
    evaluate_byox_code_manifest,
)


BYOX_CODE_AUDIT_SCHEMA_VERSION = 2
BYOX_CODE_AUDIT_SCOPE = "CODE_PRESENCE_STRUCTURE_ONLY"
BYOX_CODE_AUDIT_PROTOCOL = "IMMUTABLE_MANIFEST_V1"
DEFAULT_MAX_AUDIT_ARTIFACTS = 100
MAX_AUDIT_ARTIFACTS = 1_000
DEFAULT_MAX_AUDIT_TOTAL_BYTES = 512 * 1024 * 1024
MAX_AUDIT_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
DEFAULT_MAX_AUDIT_WALL_SECONDS = 15 * 60.0
MAX_AUDIT_WALL_SECONDS = 60 * 60.0
MAX_CONTROLLER_VALIDATIONS = 50
MAX_CONTROLLER_EVIDENCE_BYTES = 2 * 1024 * 1024
MAX_EXISTING_AUDIT_ROWS = 100_000
MAX_ARTIFACT_ALIAS_ROWS = 100_000
_EXPLICIT_ID_QUERY_CHUNK = 400

# A complete archive checksum is performed before the narrower policy replay.
# Keeping these ceilings at least as strict as the gate makes both execution
# and retained evidence bounded, including for a corrupt database path.
_TREE_MAX_ENTRIES = 20_000
_TREE_MAX_FILES = 10_000
_TREE_MAX_TOTAL_BYTES = 256 * 1024 * 1024
_TREE_MAX_FILE_BYTES = 32 * 1024 * 1024
_SNAPSHOT_PARENT_NAME = ".byox-code-audit-tmp"
_SNAPSHOT_PREFIX = "snapshot-"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AUDIT_IDENTITY = re.compile(r"^[A-Za-z0-9_.-]{1,200}$")
_ARTIFACT_POLICIES = {
    "byox-challenge-pack": "byox_reference_build",
    "byox-remediated-challenge-pack": "byox_reference_repair",
}


class ByoxGateBackfillError(RuntimeError):
    """The maintenance audit cannot safely bind or append its evidence."""


class _TreeAuditFailure(ByoxGateBackfillError):
    def __init__(self, code: str, **details: Any):
        super().__init__(code)
        self.code = code
        self.details = details


class _InvocationBudgetExhausted(ByoxGateBackfillError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class _Policy:
    name: str
    digest: str
    specification: dict[str, Any]
    specification_json: str
    specification_sha256: str


@dataclass(frozen=True)
class _ArtifactSnapshot:
    artifact_id: str
    job_id: str
    artifact_type: str
    path: str
    checksum: str
    checksum_algorithm: str
    integrity_status: str
    artifact_attempt: int
    artifact_created_at: float
    job_state: str
    job_attempt_count: int
    payload_json: str
    payload_sha256: str


@dataclass(frozen=True)
class _TreeSnapshot:
    checksum: str
    entries: int
    files: int
    total_bytes: int


@dataclass(frozen=True)
class _SnapshotCopy:
    tree: _TreeSnapshot
    manifest: ByoxCodeManifest
    manifest_digest: str
    policy_manifest_digest: str
    manifest_tree_checksum: str


@dataclass
class _InvocationBudget:
    max_total_bytes: int
    deadline: float
    consumed_total_bytes: int = 0

    @property
    def remaining_total_bytes(self) -> int:
        return self.max_total_bytes - self.consumed_total_bytes

    def check_time(self) -> None:
        _check_deadline(self.deadline)

    def consume_read(self, byte_count: int) -> None:
        """Charge bytes actually read, including reads from rejected trees."""

        if byte_count < 0 or byte_count > self.remaining_total_bytes:
            raise _InvocationBudgetExhausted("max_total_bytes")
        self.consumed_total_bytes += byte_count

    def next_read_size(self, expected_remaining: int, maximum: int) -> int:
        self.check_time()
        if expected_remaining <= 0:
            return 0
        allowed = min(expected_remaining, maximum, self.remaining_total_bytes)
        if allowed <= 0:
            raise _InvocationBudgetExhausted("max_total_bytes")
        return allowed


def revalidate_archived_byox_artifacts(
    db: Database,
    warehouse: Path,
    *,
    max_artifacts: int = DEFAULT_MAX_AUDIT_ARTIFACTS,
    max_total_bytes: int = DEFAULT_MAX_AUDIT_TOTAL_BYTES,
    max_wall_seconds: float = DEFAULT_MAX_AUDIT_WALL_SECONDS,
    artifact_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Append bounded structural-policy observations for archived BYOX packs.

    This function never changes jobs, artifacts, validations, labels, or files.
    A repeated identical observation resolves to its existing deterministic row.
    A later different observation is appended and the binding's effective result
    becomes ``CONFLICT`` rather than replacing earlier evidence.
    """

    _validate_max_artifacts(max_artifacts)
    _validate_max_total_bytes(max_total_bytes)
    _validate_max_wall_seconds(max_wall_seconds)
    budget = _InvocationBudget(
        max_total_bytes=max_total_bytes,
        deadline=_monotonic() + float(max_wall_seconds),
    )
    policy = _current_policy()
    requested = _validated_artifact_ids(artifact_ids, max_artifacts)
    _assert_policy_ledger_consistency(db, policy)
    snapshots = _select_artifacts(db, policy, max_artifacts, requested)

    records: list[dict[str, Any]] = []
    stopped_reason: str | None = None
    stopped_artifact_id: str | None = None
    for snapshot in snapshots:
        try:
            budget.check_time()
            observation = _observe_artifact(
                db,
                warehouse,
                snapshot,
                policy,
                budget,
            )
            # An observation that completed after the invocation deadline is
            # not durable evidence.  Leave it eligible for a later run.
            budget.check_time()
            record = _append_observation(
                db,
                snapshot,
                policy,
                observation,
                deadline=budget.deadline,
            )
        except _InvocationBudgetExhausted as error:
            stopped_reason = error.reason
            stopped_artifact_id = snapshot.artifact_id
            break
        records.append(record)

    outcomes: dict[str, int] = {}
    for record in records:
        outcome = str(record["effective_outcome"])
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    return {
        "policy_name": policy.name,
        "policy_digest": policy.digest,
        "policy_spec_sha256": policy.specification_sha256,
        "scope": BYOX_CODE_AUDIT_SCOPE,
        "semantic_claims_added": [],
        "builds_or_tested_claimed": False,
        "selected": len(snapshots),
        "processed": len(records),
        "inserted": sum(bool(record["inserted"]) for record in records),
        "already_recorded": sum(not bool(record["inserted"]) for record in records),
        "effective_outcomes": dict(sorted(outcomes.items())),
        "remaining_unaudited": _remaining_unaudited(db, policy),
        "stopped_reason": stopped_reason,
        "stopped_artifact_id": stopped_artifact_id,
        "budget": {
            "max_artifacts": max_artifacts,
            "max_total_bytes": max_total_bytes,
            "max_wall_seconds": float(max_wall_seconds),
            "consumed_total_bytes": budget.consumed_total_bytes,
        },
        "records": records,
    }


def _current_policy() -> _Policy:
    matches = [
        specification
        for specification in byox_runtime_safety_validators()
        if specification.get("name") == BYOX_CODE_PRESENCE_VALIDATOR
    ]
    if len(matches) != 1:
        raise ByoxGateBackfillError(
            "current BYOX runtime policy lacks exactly one code-presence validator"
        )
    specification = matches[0]
    if (
        specification.get("type") != "byox_code_presence"
        or specification.get("claims") != ["PARTIAL"]
    ):
        raise ByoxGateBackfillError("current BYOX code-presence specification is unsafe")
    specification_json = canonical_json(specification)
    digest = byox_code_policy_digest()
    if _SHA256.fullmatch(digest) is None:
        raise ByoxGateBackfillError("current BYOX code policy digest is malformed")
    return _Policy(
        name=BYOX_CODE_PRESENCE_VALIDATOR,
        digest=digest,
        specification=specification,
        specification_json=specification_json,
        specification_sha256=_sha256_text(specification_json),
    )


def _validate_max_artifacts(value: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MAX_AUDIT_ARTIFACTS
    ):
        raise ByoxGateBackfillError(
            f"max_artifacts must be from 1 through {MAX_AUDIT_ARTIFACTS}"
        )


def _validate_max_total_bytes(value: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MAX_AUDIT_TOTAL_BYTES
    ):
        raise ByoxGateBackfillError(
            "max_total_bytes must be from 1 through "
            f"{MAX_AUDIT_TOTAL_BYTES}"
        )


def _validate_max_wall_seconds(value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or not 0 < float(value) <= MAX_AUDIT_WALL_SECONDS
    ):
        raise ByoxGateBackfillError(
            "max_wall_seconds must be finite and greater than zero through "
            f"{MAX_AUDIT_WALL_SECONDS:g}"
        )


def _monotonic() -> float:
    return time.monotonic()


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None and _monotonic() >= deadline:
        raise _InvocationBudgetExhausted("max_wall_seconds")


def _validated_artifact_ids(
    values: Sequence[str] | None, max_artifacts: int
) -> tuple[str, ...] | None:
    if values is None:
        return None
    identifiers = tuple(values)
    if not identifiers:
        return ()
    if len(identifiers) > max_artifacts:
        raise ByoxGateBackfillError("requested artifact count exceeds max_artifacts")
    if len(set(identifiers)) != len(identifiers):
        raise ByoxGateBackfillError("artifact IDs must be unique")
    if any(
        not isinstance(identifier, str)
        or _AUDIT_IDENTITY.fullmatch(identifier) is None
        for identifier in identifiers
    ):
        raise ByoxGateBackfillError("artifact IDs must be bounded safe identifiers")
    return tuple(sorted(identifiers))


def _select_artifacts(
    db: Database,
    policy: _Policy,
    max_artifacts: int,
    requested: tuple[str, ...] | None,
) -> tuple[_ArtifactSnapshot, ...]:
    base_select = """
        SELECT a.artifact_id,a.job_id,a.type AS artifact_type,a.path,
               a.checksum,a.checksum_algorithm,a.integrity_status,
               a.attempt_number AS artifact_attempt,
               a.created_at AS artifact_created_at,
               j.state AS job_state,j.attempt_count AS job_attempt_count,
               j.payload_json
        FROM artifacts AS a
        JOIN jobs AS j ON j.job_id=a.job_id
    """
    if requested is not None:
        rows: list[sqlite3.Row] = []
        with db.connect() as connection:
            for offset in range(0, len(requested), _EXPLICIT_ID_QUERY_CHUNK):
                chunk = requested[offset : offset + _EXPLICIT_ID_QUERY_CHUNK]
                rows.extend(
                    connection.execute(
                        base_select
                        + f"""
                        WHERE a.type IN ({','.join('?' for _ in _ARTIFACT_POLICIES)})
                          AND a.artifact_id IN ({','.join('?' for _ in chunk)})
                        """,
                        (*_ARTIFACT_POLICIES, *chunk),
                    )
                )
            found = {str(row["artifact_id"]) for row in rows}
            missing = sorted(set(requested) - found)
            if missing:
                raise ByoxGateBackfillError(
                    "requested artifacts are missing or are not BYOX challenge packs: "
                    + ", ".join(missing)
                )
        rows.sort(key=lambda row: (float(row["artifact_created_at"]), str(row["artifact_id"])))
        return tuple(_snapshot(row) for row in rows)

    with db.connect() as connection:
        rows = list(
            connection.execute(
                base_select
                + f"""
                WHERE a.type IN ({','.join('?' for _ in _ARTIFACT_POLICIES)})
                  AND NOT EXISTS (
                    SELECT 1 FROM byox_code_presence_audits AS audit
                    WHERE audit.artifact_id=a.artifact_id
                      AND audit.policy_name=?
                      AND audit.policy_digest=?
                  )
                ORDER BY a.created_at,a.artifact_id
                LIMIT ?
                """,
                (*_ARTIFACT_POLICIES, policy.name, policy.digest, max_artifacts),
            )
        )
    return tuple(_snapshot(row) for row in rows)


def _snapshot(row: sqlite3.Row) -> _ArtifactSnapshot:
    payload_json = str(row["payload_json"])
    return _ArtifactSnapshot(
        artifact_id=str(row["artifact_id"]),
        job_id=str(row["job_id"]),
        artifact_type=str(row["artifact_type"]),
        path=str(row["path"]),
        checksum=str(row["checksum"]),
        checksum_algorithm=str(row["checksum_algorithm"]),
        integrity_status=str(row["integrity_status"]),
        artifact_attempt=int(row["artifact_attempt"]),
        artifact_created_at=float(row["artifact_created_at"]),
        job_state=str(row["job_state"]),
        job_attempt_count=int(row["job_attempt_count"]),
        payload_json=payload_json,
        payload_sha256=_sha256_text(payload_json),
    )


def _observe_artifact(
    db: Database,
    warehouse: Path,
    artifact: _ArtifactSnapshot,
    policy: _Policy,
    budget: _InvocationBudget,
) -> dict[str, Any]:
    budget.check_time()
    errors = _identity_errors(db, artifact)
    budget.check_time()
    observed_checksum: str | None = None
    archive_relative: str | None = None
    tree_evidence: dict[str, Any] = {
        "status": "NOT_RUN",
        "audit_protocol": BYOX_CODE_AUDIT_PROTOCOL,
    }
    gate_status = "NOT_RUN"
    gate_evidence: dict[str, Any] = {}
    reason_codes: list[str] = list(errors)
    unexpected_error = False

    if not errors:
        try:
            artifact_path, archive_relative = _checked_archive_path(
                warehouse, artifact.path
            )
            source_before = _bounded_tree_checksum(
                artifact_path,
                deadline=budget.deadline,
                budget=budget,
            )
            observed_checksum = source_before.checksum
            tree_evidence = {
                "status": "CHECKED",
                "audit_protocol": BYOX_CODE_AUDIT_PROTOCOL,
                "passes": 1,
                "source_hash_passes": 1,
                "snapshot_hash_passes": 0,
                "entries": source_before.entries,
                "files": source_before.files,
                "total_bytes": source_before.total_bytes,
                "observed_checksum": observed_checksum,
                "matches_stored_checksum": observed_checksum == artifact.checksum,
            }
            if observed_checksum != artifact.checksum:
                reason_codes.append("checksum-drift")
            else:
                with _private_archive_snapshot(
                    warehouse,
                    artifact_path,
                    deadline=budget.deadline,
                    budget=budget,
                ) as (snapshot_path, copied):
                    snapshot_before = copied.tree
                    source_after_copy = _bounded_tree_checksum(
                        artifact_path,
                        deadline=budget.deadline,
                        budget=budget,
                    )
                    observed_checksum = source_after_copy.checksum
                    if snapshot_before.checksum != artifact.checksum:
                        raise _TreeAuditFailure(
                            "private-snapshot-checksum-mismatch",
                            observed_checksum=observed_checksum,
                            snapshot_checksum=snapshot_before.checksum,
                        )
                    if copied.manifest_tree_checksum != artifact.checksum:
                        raise _TreeAuditFailure(
                            "immutable-manifest-checksum-mismatch",
                            observed_checksum=observed_checksum,
                            snapshot_checksum=snapshot_before.checksum,
                            manifest_tree_checksum=copied.manifest_tree_checksum,
                            manifest_digest=copied.manifest_digest,
                        )
                    if source_after_copy.checksum != artifact.checksum:
                        raise _TreeAuditFailure(
                            "source-changed-during-snapshot",
                            observed_checksum=observed_checksum,
                            snapshot_checksum=snapshot_before.checksum,
                        )
                    try:
                        budget.check_time()
                        gate = evaluate_byox_code_manifest(
                            copied.manifest,
                            policy.specification,
                            name=policy.name,
                        )
                        gate_status = (
                            gate.status
                            if gate.status in {"PASS", "FAIL", "ERROR"}
                            else "ERROR"
                        )
                        gate_evidence = gate.evidence
                        if gate_evidence.get("policy_digest") != policy.digest:
                            gate_status = "ERROR"
                            reason_codes.append("policy-digest-mismatch")
                        elif (
                            gate_evidence.get("manifest_digest")
                            != copied.policy_manifest_digest
                        ):
                            gate_status = "ERROR"
                            reason_codes.append("manifest-digest-mismatch")
                        elif gate_status != "PASS":
                            reason_codes.append(f"gate-{gate_status.casefold()}")
                        budget.check_time()
                    except _InvocationBudgetExhausted:
                        raise
                    except Exception as error:  # fail closed without source contents
                        gate_status = "ERROR"
                        gate_evidence = {"error_type": error.__class__.__name__}
                        reason_codes.append("gate-execution-error")
                        unexpected_error = True
                    snapshot_after = _bounded_tree_checksum(
                        snapshot_path,
                        deadline=budget.deadline,
                        budget=budget,
                    )
                    if snapshot_after != snapshot_before:
                        raise _TreeAuditFailure(
                            "private-snapshot-changed-during-policy-replay",
                            observed_checksum=observed_checksum,
                            snapshot_checksum=snapshot_before.checksum,
                            post_gate_snapshot_checksum=snapshot_after.checksum,
                            manifest_tree_checksum=copied.manifest_tree_checksum,
                            manifest_digest=copied.manifest_digest,
                        )
                    source_after_gate = _bounded_tree_checksum(
                        artifact_path,
                        deadline=budget.deadline,
                        budget=budget,
                    )
                    observed_checksum = source_after_gate.checksum
                    if source_after_gate.checksum != artifact.checksum:
                        raise _TreeAuditFailure(
                            "tree-changed-during-policy-replay",
                            observed_checksum=observed_checksum,
                            snapshot_checksum=snapshot_before.checksum,
                            post_gate_snapshot_checksum=snapshot_after.checksum,
                            manifest_tree_checksum=copied.manifest_tree_checksum,
                            manifest_digest=copied.manifest_digest,
                        )
                    tree_evidence = {
                        "status": "CHECKED",
                        "audit_protocol": BYOX_CODE_AUDIT_PROTOCOL,
                        "passes": 5,
                        "source_hash_passes": 3,
                        "snapshot_hash_passes": 2,
                        "entries": snapshot_after.entries,
                        "files": snapshot_after.files,
                        "total_bytes": snapshot_after.total_bytes,
                        "observed_checksum": observed_checksum,
                        "snapshot_checksum": snapshot_before.checksum,
                        "post_gate_snapshot_checksum": snapshot_after.checksum,
                        "manifest_tree_checksum": copied.manifest_tree_checksum,
                        "manifest_digest": copied.manifest_digest,
                        "policy_manifest_digest": copied.policy_manifest_digest,
                        "matches_stored_checksum": (
                            observed_checksum
                            == snapshot_before.checksum
                            == snapshot_after.checksum
                            == artifact.checksum
                        ),
                    }
        except _TreeAuditFailure as error:
            details = dict(error.details)
            if observed_checksum is not None:
                details.setdefault("observed_checksum", observed_checksum)
            tree_evidence = {
                "status": "REJECTED",
                "audit_protocol": BYOX_CODE_AUDIT_PROTOCOL,
                "reason": error.code,
                **details,
            }
            reason_codes.append(error.code)
        except (OSError, ValueError) as error:
            tree_evidence = {
                "status": "ERROR",
                "audit_protocol": BYOX_CODE_AUDIT_PROTOCOL,
                "error_type": error.__class__.__name__,
            }
            if observed_checksum is not None:
                tree_evidence["observed_checksum"] = observed_checksum
            reason_codes.append("archive-read-error")
            unexpected_error = True

    controller, controller_conflict = _controller_evidence(
        db, artifact, policy, gate_status, gate_evidence
    )
    if controller_conflict:
        reason_codes.append("conflicting-controller-evidence")

    if controller_conflict:
        base_outcome = "CONFLICT"
    elif unexpected_error or gate_status == "ERROR":
        base_outcome = "ERROR"
    elif reason_codes or gate_status != "PASS":
        base_outcome = "FAIL"
    else:
        base_outcome = "PASS"

    return {
        "schema_version": BYOX_CODE_AUDIT_SCHEMA_VERSION,
        "audit_protocol": BYOX_CODE_AUDIT_PROTOCOL,
        "scope": BYOX_CODE_AUDIT_SCOPE,
        "artifact": {
            "artifact_id": artifact.artifact_id,
            "job_id": artifact.job_id,
            "artifact_type": artifact.artifact_type,
            "artifact_attempt": artifact.artifact_attempt,
            "artifact_checksum": artifact.checksum,
            "checksum_algorithm": artifact.checksum_algorithm,
            "integrity_status": artifact.integrity_status,
            "archive_relative_path": archive_relative,
            "job_state": artifact.job_state,
            "job_attempt_count": artifact.job_attempt_count,
            "job_payload_sha256": artifact.payload_sha256,
        },
        "policy": {
            "name": policy.name,
            "digest": policy.digest,
            "specification_sha256": policy.specification_sha256,
        },
        "identity_errors": errors,
        "archive_tree": tree_evidence,
        "gate": {"status": gate_status, "evidence": gate_evidence},
        "controller_evidence": controller,
        "controller_evidence_sha256": _sha256_json(controller),
        "reason_codes": sorted(set(reason_codes)),
        "base_outcome": base_outcome,
        "semantic_claims_added": [],
        "claims_builds_or_tested": False,
    }


def _identity_errors(
    db: Database,
    artifact: _ArtifactSnapshot,
    *,
    connection: sqlite3.Connection | None = None,
) -> list[str]:
    errors: list[str] = []
    if _AUDIT_IDENTITY.fullmatch(artifact.artifact_id) is None:
        errors.append("malformed-artifact-id")
    if _AUDIT_IDENTITY.fullmatch(artifact.job_id) is None:
        errors.append("malformed-job-id")
    if artifact.artifact_type not in _ARTIFACT_POLICIES:
        errors.append("unsupported-artifact-type")
    if artifact.artifact_attempt < 1:
        errors.append("invalid-artifact-attempt")
    if artifact.job_state != "SUCCEEDED":
        errors.append("job-not-succeeded")
    if artifact.job_attempt_count != artifact.artifact_attempt:
        errors.append("job-artifact-attempt-mismatch")
    if artifact.checksum_algorithm != "tree-sha256-v2":
        errors.append("unsupported-checksum-algorithm")
    if _SHA256.fullmatch(artifact.checksum) is None:
        errors.append("malformed-artifact-checksum")
    if artifact.integrity_status != "VERIFIED_V2":
        errors.append("artifact-integrity-not-verified-v2")

    try:
        payload = _strict_json_object(artifact.payload_json)
    except ValueError:
        payload = {}
        errors.append("malformed-job-payload")
    expected_kind = _ARTIFACT_POLICIES.get(artifact.artifact_type)
    seed_policy = payload.get("seed_policy")
    if (
        not isinstance(seed_policy, dict)
        or seed_policy.get("kind") != expected_kind
        or seed_policy.get("role") != "builder"
    ):
        errors.append("job-policy-binding-mismatch")
    if payload.get("artifact_type") != artifact.artifact_type:
        errors.append("job-artifact-type-mismatch")
    if not isinstance(payload.get("project_id"), str) or not payload["project_id"].strip():
        errors.append("job-project-binding-missing")

    def inspect(connected: sqlite3.Connection) -> tuple[int, int, list[sqlite3.Row]]:
        return (
            int(
                connected.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE job_id=? AND attempt_number=?",
                    (artifact.job_id, artifact.artifact_attempt),
                ).fetchone()[0]
            ),
            int(
                connected.execute(
                    "SELECT COUNT(*) FROM artifacts WHERE path=?", (artifact.path,)
                ).fetchone()[0]
            ),
            list(
                connected.execute(
                    """
                    SELECT artifact_id,path FROM artifacts
                    ORDER BY artifact_id LIMIT ?
                    """,
                    (MAX_ARTIFACT_ALIAS_ROWS + 1,),
                )
            ),
        )
    if connection is None:
        with db.connect() as owned:
            same_attempt, same_path, artifact_paths = inspect(owned)
    else:
        same_attempt, same_path, artifact_paths = inspect(connection)
    if same_attempt != 1:
        errors.append("ambiguous-job-attempt-artifacts")
    if same_path != 1:
        errors.append("ambiguous-artifact-path")
    if len(artifact_paths) > MAX_ARTIFACT_ALIAS_ROWS:
        errors.append("artifact-alias-scan-limit-exceeded")
    else:
        normalized = os.path.abspath(artifact.path)
        aliases = [
            row
            for row in artifact_paths
            if row["artifact_id"] != artifact.artifact_id
            and os.path.abspath(str(row["path"])) == normalized
        ]
        if aliases:
            errors.append("ambiguous-normalized-artifact-path")
    return sorted(set(errors))


def _checked_archive_path(warehouse: Path, stored_path: str) -> tuple[Path, str]:
    base = Path(os.path.abspath(warehouse / "artifacts"))
    canonical = os.path.abspath(stored_path)
    if stored_path != canonical:
        raise _TreeAuditFailure("artifact-path-not-canonical")
    path = Path(canonical)
    if not path.is_absolute():
        raise _TreeAuditFailure("artifact-path-not-absolute")
    try:
        relative = path.relative_to(base)
    except ValueError as error:
        raise _TreeAuditFailure("artifact-path-outside-warehouse") from error
    if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise _TreeAuditFailure("artifact-path-not-canonical")
    try:
        if base.resolve(strict=True) != base:
            raise _TreeAuditFailure("warehouse-artifacts-has-symlink-component")
    except FileNotFoundError as error:
        raise _TreeAuditFailure("warehouse-artifacts-missing") from error

    current = base
    for part in relative.parts:
        current = current / part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError as error:
            raise _TreeAuditFailure("artifact-path-missing") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise _TreeAuditFailure(
                "artifact-path-symlink-component", path=current.relative_to(base).as_posix()
            )
        if not stat.S_ISDIR(metadata.st_mode):
            raise _TreeAuditFailure(
                "artifact-path-nondirectory-component",
                path=current.relative_to(base).as_posix(),
            )
    return path, relative.as_posix()


@contextlib.contextmanager
def _private_archive_snapshot(
    warehouse: Path,
    source_root: Path,
    *,
    deadline: float | None = None,
    budget: _InvocationBudget | None = None,
) -> Iterator[tuple[Path, _SnapshotCopy]]:
    """Yield a bounded private copy and remove it on every exit path.

    The copy routine opens every source entry relative to an already opened
    directory with ``O_NOFOLLOW`` and preserves the file mode bits included by
    ``tree-sha256-v2``.  It also returns the immutable metadata/content-hash
    manifest consumed by the structural gate; the gate never rescans this path.
    """

    parent = _private_snapshot_parent(warehouse)
    snapshot_root: Path | None = None
    primary_error: BaseException | None = None
    try:
        snapshot_root = Path(
            tempfile.mkdtemp(prefix=_SNAPSHOT_PREFIX, dir=parent)
        )
        metadata = os.lstat(snapshot_root)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_mode & 0o777 != 0o700
        ):
            raise _TreeAuditFailure("private-snapshot-not-private")
        copied = _copy_bounded_tree(
            source_root,
            snapshot_root,
            deadline=deadline,
            budget=budget,
        )
        yield snapshot_root, copied
    except BaseException as error:
        primary_error = error
        raise
    finally:
        if snapshot_root is not None:
            try:
                _discard_private_snapshot(snapshot_root)
            except Exception as error:
                if isinstance(primary_error, _InvocationBudgetExhausted):
                    primary_error.add_note(
                        "private snapshot cleanup also failed: "
                        f"{error.__class__.__name__}"
                    )
                else:
                    raise _TreeAuditFailure(
                        "private-snapshot-cleanup-failed",
                        error_type=error.__class__.__name__,
                    ) from error


def _private_snapshot_parent(warehouse: Path) -> Path:
    warehouse_root = Path(os.path.abspath(warehouse))
    try:
        metadata = os.lstat(warehouse_root)
        resolved = warehouse_root.resolve(strict=True)
    except (FileNotFoundError, OSError) as error:
        raise _TreeAuditFailure(
            "snapshot-warehouse-unavailable", error_type=error.__class__.__name__
        ) from error
    if (
        resolved != warehouse_root
        or stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
    ):
        raise _TreeAuditFailure("snapshot-warehouse-unsafe")

    parent = warehouse_root / _SNAPSHOT_PARENT_NAME
    created = False
    try:
        os.mkdir(parent, 0o700)
        created = True
    except FileExistsError:
        pass
    except OSError as error:
        raise _TreeAuditFailure(
            "snapshot-parent-unavailable", error_type=error.__class__.__name__
        ) from error
    try:
        if created:
            _chmod_opened_path(parent, 0o700, directory=True)
        parent_metadata = os.lstat(parent)
    except OSError as error:
        raise _TreeAuditFailure(
            "snapshot-parent-unavailable", error_type=error.__class__.__name__
        ) from error
    if (
        stat.S_ISLNK(parent_metadata.st_mode)
        or not stat.S_ISDIR(parent_metadata.st_mode)
        or parent_metadata.st_uid != os.geteuid()
        or parent_metadata.st_mode & 0o777 != 0o700
    ):
        raise _TreeAuditFailure("snapshot-parent-not-private")
    return parent


def _copy_bounded_tree(
    source_root: Path,
    destination_root: Path,
    *,
    deadline: float | None = None,
    budget: _InvocationBudget | None = None,
) -> _SnapshotCopy:
    _check_deadline(deadline)
    counters = {"entries": 0, "files": 0, "total_bytes": 0}
    manifest_entries: list[ByoxCodeManifestEntry] = []
    directory_flags = _tree_directory_flags()
    source_descriptor, root_before = _open_absolute_tree_root(source_root)
    try:
        _copy_bounded_directory(
            source_descriptor,
            destination_root,
            relative_prefix="",
            depth=0,
            counters=counters,
            directory_flags=directory_flags,
            manifest_entries=manifest_entries,
            deadline=deadline,
            budget=budget,
        )
        root_after = os.fstat(source_descriptor)
        if not _same_file_snapshot(root_before, root_after):
            raise _TreeAuditFailure("snapshot-source-root-changed")
    finally:
        os.close(source_descriptor)
    rebound_descriptor, root_rebound = _open_absolute_tree_root(source_root)
    os.close(rebound_descriptor)
    if not _same_file_snapshot(root_before, root_rebound):
        raise _TreeAuditFailure("snapshot-source-root-changed")

    copied = _bounded_tree_checksum(
        destination_root,
        deadline=deadline,
        budget=budget,
    )
    if (
        copied.entries != counters["entries"]
        or copied.files != counters["files"]
        or copied.total_bytes != counters["total_bytes"]
    ):
        raise _TreeAuditFailure("private-snapshot-copy-count-mismatch")
    manifest = ByoxCodeManifest(
        entries=tuple(sorted(manifest_entries, key=lambda entry: entry.path)),
        scope="full-tree",
    )
    try:
        manifest_tree_checksum = byox_code_manifest_tree_sha256(manifest)
    except ValueError as error:
        raise _TreeAuditFailure("immutable-manifest-invalid") from error
    if manifest_tree_checksum != copied.checksum:
        raise _TreeAuditFailure(
            "immutable-manifest-snapshot-mismatch",
            snapshot_checksum=copied.checksum,
            manifest_tree_checksum=manifest_tree_checksum,
        )
    return _SnapshotCopy(
        tree=copied,
        manifest=manifest,
        manifest_digest=byox_code_manifest_digest(manifest),
        policy_manifest_digest=byox_code_policy_manifest_digest(manifest),
        manifest_tree_checksum=manifest_tree_checksum,
    )


def _copy_bounded_directory(
    source_descriptor: int,
    destination: Path,
    *,
    relative_prefix: str,
    depth: int,
    counters: dict[str, int],
    directory_flags: int,
    manifest_entries: list[ByoxCodeManifestEntry],
    deadline: float | None = None,
    budget: _InvocationBudget | None = None,
) -> None:
    _check_deadline(deadline)
    if depth > BYOX_TREE_MAX_DEPTH:
        raise _TreeAuditFailure(
            "max-depth-exceeded", maximum=BYOX_TREE_MAX_DEPTH
        )
    try:
        with os.scandir(source_descriptor) as iterator:
            entries: list[os.DirEntry[str]] = []
            for entry in iterator:
                _check_deadline(deadline)
                entries.append(entry)
                if counters["entries"] + len(entries) > _TREE_MAX_ENTRIES:
                    raise _TreeAuditFailure(
                        "max-entries-exceeded", maximum=_TREE_MAX_ENTRIES
                    )
    except OSError as error:
        raise _TreeAuditFailure(
            "snapshot-source-directory-unreadable",
            error_type=error.__class__.__name__,
        ) from error
    entries.sort(key=lambda entry: entry.name)

    for entry in entries:
        _check_deadline(deadline)
        counters["entries"] += 1
        if counters["entries"] > _TREE_MAX_ENTRIES:
            raise _TreeAuditFailure("max-entries-exceeded", maximum=_TREE_MAX_ENTRIES)
        relative = (
            f"{relative_prefix}/{entry.name}" if relative_prefix else entry.name
        )
        try:
            expected = entry.stat(follow_symlinks=False)
        except OSError as error:
            raise _TreeAuditFailure(
                "snapshot-source-entry-unreadable",
                path=relative,
                error_type=error.__class__.__name__,
            ) from error
        destination_path = destination / entry.name
        mode = expected.st_mode
        if stat.S_ISLNK(mode):
            raise _TreeAuditFailure("symlink-entry", path=relative)
        if stat.S_ISDIR(mode):
            if depth >= BYOX_TREE_MAX_DEPTH:
                raise _TreeAuditFailure(
                    "max-depth-exceeded",
                    path=relative,
                    maximum=BYOX_TREE_MAX_DEPTH,
                )
            try:
                child_descriptor = os.open(
                    entry.name, directory_flags, dir_fd=source_descriptor
                )
            except OSError as error:
                raise _TreeAuditFailure(
                    "snapshot-source-directory-unreadable",
                    path=relative,
                    error_type=error.__class__.__name__,
                ) from error
            try:
                child_before = os.fstat(child_descriptor)
                if (
                    not stat.S_ISDIR(child_before.st_mode)
                    or not _same_file_snapshot(expected, child_before)
                ):
                    raise _TreeAuditFailure(
                        "snapshot-source-directory-changed", path=relative
                    )
                os.mkdir(destination_path, 0o700)
                manifest_entries.append(
                    ByoxCodeManifestEntry(
                        relative,
                        "directory",
                        mode=mode & 0o777,
                    )
                )
                _copy_bounded_directory(
                    child_descriptor,
                    destination_path,
                    relative_prefix=relative,
                    depth=depth + 1,
                    counters=counters,
                    directory_flags=directory_flags,
                    manifest_entries=manifest_entries,
                    deadline=deadline,
                    budget=budget,
                )
                child_after = os.fstat(child_descriptor)
                if not _same_file_snapshot(child_before, child_after):
                    raise _TreeAuditFailure(
                        "snapshot-source-directory-changed", path=relative
                    )
            finally:
                os.close(child_descriptor)
            continue
        if not stat.S_ISREG(mode):
            raise _TreeAuditFailure("special-file-entry", path=relative)
        if expected.st_nlink != 1:
            raise _TreeAuditFailure("hardlink-entry", path=relative)

        counters["files"] += 1
        if counters["files"] > _TREE_MAX_FILES:
            raise _TreeAuditFailure("max-files-exceeded", maximum=_TREE_MAX_FILES)
        if expected.st_size > _TREE_MAX_FILE_BYTES:
            raise _TreeAuditFailure(
                "max-file-bytes-exceeded",
                path=relative,
                size_bytes=expected.st_size,
                maximum=_TREE_MAX_FILE_BYTES,
            )
        counters["total_bytes"] += expected.st_size
        if counters["total_bytes"] > _TREE_MAX_TOTAL_BYTES:
            raise _TreeAuditFailure(
                "max-total-bytes-exceeded", maximum=_TREE_MAX_TOTAL_BYTES
            )
        file_digest = _copy_regular_file_from_directory(
            source_descriptor,
            entry.name,
            destination_path,
            expected,
            relative,
            deadline=deadline,
            budget=budget,
        )
        manifest_entries.append(
            ByoxCodeManifestEntry(
                relative,
                "file",
                mode=mode & 0o777,
                size_bytes=expected.st_size,
                sha256=file_digest,
            )
        )


def _copy_regular_file_from_directory(
    source_directory_descriptor: int,
    name: str,
    destination: Path,
    expected: os.stat_result,
    relative: str,
    *,
    deadline: float | None = None,
    budget: _InvocationBudget | None = None,
) -> str:
    _check_deadline(deadline)
    source_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    source_flags |= getattr(os, "O_NOFOLLOW", 0)
    source_flags |= getattr(os, "O_NONBLOCK", 0)
    destination_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    destination_flags |= getattr(os, "O_CLOEXEC", 0)
    destination_flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        source_descriptor = os.open(
            name,
            source_flags,
            dir_fd=source_directory_descriptor,
        )
    except OSError as error:
        raise _TreeAuditFailure(
            "snapshot-source-file-unreadable",
            path=relative,
            error_type=error.__class__.__name__,
        ) from error
    try:
        before = os.fstat(source_descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or not _same_file_snapshot(expected, before)
        ):
            raise _TreeAuditFailure("snapshot-source-file-changed", path=relative)
        try:
            destination_descriptor = os.open(
                destination,
                destination_flags,
                0o600,
            )
        except OSError as error:
            raise _TreeAuditFailure(
                "private-snapshot-file-create-failed",
                path=relative,
                error_type=error.__class__.__name__,
            ) from error
        copied_bytes = 0
        source_digest = hashlib.sha256()
        try:
            while copied_bytes < before.st_size:
                _check_deadline(deadline)
                expected_remaining = before.st_size - copied_bytes
                read_size = (
                    budget.next_read_size(expected_remaining, 1024 * 1024)
                    if budget is not None
                    else min(expected_remaining, 1024 * 1024)
                )
                chunk = os.read(source_descriptor, read_size)
                if not chunk:
                    raise _TreeAuditFailure(
                        "snapshot-source-file-changed", path=relative
                    )
                if budget is not None:
                    budget.consume_read(len(chunk))
                copied_bytes += len(chunk)
                if copied_bytes > _TREE_MAX_FILE_BYTES:
                    raise _TreeAuditFailure(
                        "max-file-bytes-exceeded",
                        path=relative,
                        maximum=_TREE_MAX_FILE_BYTES,
                    )
                source_digest.update(chunk)
                remaining = memoryview(chunk)
                while remaining:
                    _check_deadline(deadline)
                    written = os.write(destination_descriptor, remaining)
                    if written <= 0:
                        raise _TreeAuditFailure(
                            "private-snapshot-short-write", path=relative
                        )
                    remaining = remaining[written:]
            os.fchmod(destination_descriptor, before.st_mode & 0o777)
            copied_metadata = os.fstat(destination_descriptor)
            if (
                copied_bytes != before.st_size
                or copied_metadata.st_size != before.st_size
                or copied_metadata.st_mode & 0o777 != before.st_mode & 0o777
            ):
                raise _TreeAuditFailure(
                    "private-snapshot-file-copy-mismatch", path=relative
                )
        finally:
            os.close(destination_descriptor)
        after = os.fstat(source_descriptor)
        if not _same_file_snapshot(before, after):
            raise _TreeAuditFailure("snapshot-source-file-changed", path=relative)
    finally:
        os.close(source_descriptor)
    return source_digest.hexdigest()


def _discard_private_snapshot(snapshot_root: Path) -> None:
    try:
        metadata = os.lstat(snapshot_root)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        os.unlink(snapshot_root)
        raise OSError("private snapshot root was replaced")

    def repair_permissions(
        function: Any, raw_path: str, _error: tuple[type[BaseException], BaseException, Any]
    ) -> None:
        path = Path(raw_path)
        path_metadata = os.lstat(path)
        if not stat.S_ISLNK(path_metadata.st_mode):
            _chmod_opened_path(
                path,
                0o700 if stat.S_ISDIR(path_metadata.st_mode) else 0o600,
                directory=stat.S_ISDIR(path_metadata.st_mode),
            )
        function(raw_path)

    shutil.rmtree(snapshot_root, onerror=repair_permissions)


def _chmod_opened_path(path: Path, mode: int, *, directory: bool) -> None:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    if directory:
        flags |= getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if directory != stat.S_ISDIR(metadata.st_mode):
            raise OSError("path type changed before chmod")
        os.fchmod(descriptor, mode)
    finally:
        os.close(descriptor)


def _tree_directory_flags() -> int:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    return flags


def _open_absolute_tree_root(root: Path) -> tuple[int, os.stat_result]:
    """Open every absolute path component with ``O_NOFOLLOW`` held in turn."""

    absolute = Path(os.path.abspath(root))
    if absolute != root or not absolute.is_absolute():
        raise _TreeAuditFailure("tree-root-is-not-canonical")
    try:
        current = os.open(Path(absolute.anchor), _tree_directory_flags())
    except OSError as error:
        raise _TreeAuditFailure(
            "tree-root-unreadable", error_type=error.__class__.__name__
        ) from error
    component_depth = 0
    try:
        for part in absolute.parts[1:]:
            component_depth += 1
            try:
                expected = os.stat(
                    part,
                    dir_fd=current,
                    follow_symlinks=False,
                )
            except OSError as error:
                raise _TreeAuditFailure(
                    "tree-root-component-unreadable",
                    component_depth=component_depth,
                    error_type=error.__class__.__name__,
                ) from error
            if stat.S_ISLNK(expected.st_mode) or not stat.S_ISDIR(
                expected.st_mode
            ):
                raise _TreeAuditFailure(
                    "tree-root-component-is-not-a-directory",
                    component_depth=component_depth,
                )
            try:
                child = os.open(
                    part,
                    _tree_directory_flags(),
                    dir_fd=current,
                )
            except OSError as error:
                raise _TreeAuditFailure(
                    "tree-root-component-changed",
                    component_depth=component_depth,
                    error_type=error.__class__.__name__,
                ) from error
            try:
                actual = os.fstat(child)
            except OSError as error:
                os.close(child)
                raise _TreeAuditFailure(
                    "tree-root-component-changed",
                    component_depth=component_depth,
                    error_type=error.__class__.__name__,
                ) from error
            if not _same_file_snapshot(expected, actual):
                os.close(child)
                raise _TreeAuditFailure(
                    "tree-root-component-changed",
                    component_depth=component_depth,
                )
            os.close(current)
            current = child
        return current, os.fstat(current)
    except Exception:
        os.close(current)
        raise


def _open_tree_directory(
    root_descriptor: int,
    parts: tuple[str, ...],
    *,
    expected: os.stat_result,
    relative: str,
    deadline: float | None = None,
) -> int:
    """Open a queued directory beneath ``root_descriptor`` without aliases."""

    _check_deadline(deadline)
    current = os.dup(root_descriptor)
    try:
        for part in parts:
            _check_deadline(deadline)
            try:
                child_expected = os.stat(
                    part,
                    dir_fd=current,
                    follow_symlinks=False,
                )
            except OSError as error:
                raise _TreeAuditFailure(
                    "directory-changed-before-read",
                    path=relative,
                    error_type=error.__class__.__name__,
                ) from error
            if stat.S_ISLNK(child_expected.st_mode) or not stat.S_ISDIR(
                child_expected.st_mode
            ):
                raise _TreeAuditFailure(
                    "directory-changed-before-read", path=relative
                )
            try:
                child = os.open(
                    part,
                    _tree_directory_flags(),
                    dir_fd=current,
                )
            except OSError as error:
                raise _TreeAuditFailure(
                    "directory-changed-before-read",
                    path=relative,
                    error_type=error.__class__.__name__,
                ) from error
            try:
                child_actual = os.fstat(child)
            except OSError as error:
                os.close(child)
                raise _TreeAuditFailure(
                    "directory-changed-before-read",
                    path=relative,
                    error_type=error.__class__.__name__,
                ) from error
            if not _same_file_snapshot(child_expected, child_actual):
                os.close(child)
                raise _TreeAuditFailure(
                    "directory-changed-before-read", path=relative
                )
            os.close(current)
            current = child
        if not _same_file_snapshot(expected, os.fstat(current)):
            raise _TreeAuditFailure("directory-changed-before-read", path=relative)
        return current
    except Exception:
        os.close(current)
        raise


def _bounded_tree_checksum(
    root: Path,
    *,
    deadline: float | None = None,
    budget: _InvocationBudget | None = None,
) -> _TreeSnapshot:
    _check_deadline(deadline)
    records: list[tuple[str, str, int, bytes | None]] = []
    entries_seen = 0
    files_seen = 0
    total_bytes = 0
    root_descriptor, root_before = _open_absolute_tree_root(root)
    pending: list[tuple[str, tuple[str, ...], os.stat_result]] = [
        ("", (), root_before)
    ]
    try:
        while pending:
            _check_deadline(deadline)
            relative_directory, directory_parts, expected = heapq.heappop(pending)
            if len(directory_parts) > BYOX_TREE_MAX_DEPTH:
                raise _TreeAuditFailure(
                    "max-depth-exceeded",
                    path=relative_directory,
                    maximum=BYOX_TREE_MAX_DEPTH,
                )
            directory_descriptor = _open_tree_directory(
                root_descriptor,
                directory_parts,
                expected=expected,
                relative=relative_directory,
                deadline=deadline,
            )
            try:
                # Enter cleanup before the initial fstat.
                before = os.fstat(directory_descriptor)
                try:
                    with os.scandir(directory_descriptor) as iterator:
                        entry_names: list[str] = []
                        for entry in iterator:
                            _check_deadline(deadline)
                            entry_names.append(entry.name)
                            if (
                                entries_seen + len(entry_names)
                                > _TREE_MAX_ENTRIES
                            ):
                                raise _TreeAuditFailure(
                                    "max-entries-exceeded",
                                    maximum=_TREE_MAX_ENTRIES,
                                )
                except OSError as error:
                    raise _TreeAuditFailure(
                        "unreadable-directory",
                        path=relative_directory,
                        error_type=error.__class__.__name__,
                    ) from error
                entry_names.sort()
                for entry_name in entry_names:
                    _check_deadline(deadline)
                    entries_seen += 1
                    relative = (
                        f"{relative_directory}/{entry_name}"
                        if relative_directory
                        else entry_name
                    )
                    try:
                        metadata = os.stat(
                            entry_name,
                            dir_fd=directory_descriptor,
                            follow_symlinks=False,
                        )
                    except OSError as error:
                        raise _TreeAuditFailure(
                            "unreadable-entry",
                            path=relative,
                            error_type=error.__class__.__name__,
                        ) from error
                    mode = metadata.st_mode
                    if stat.S_ISLNK(mode):
                        raise _TreeAuditFailure("symlink-entry", path=relative)
                    if stat.S_ISDIR(mode):
                        if len(directory_parts) >= BYOX_TREE_MAX_DEPTH:
                            raise _TreeAuditFailure(
                                "max-depth-exceeded",
                                path=relative,
                                maximum=BYOX_TREE_MAX_DEPTH,
                            )
                        records.append((relative, "directory", 0, None))
                        heapq.heappush(
                            pending,
                            (
                                relative,
                                (*directory_parts, entry_name),
                                metadata,
                            ),
                        )
                        continue
                    if not stat.S_ISREG(mode):
                        raise _TreeAuditFailure("special-file-entry", path=relative)
                    if metadata.st_nlink != 1:
                        raise _TreeAuditFailure("hardlink-entry", path=relative)
                    files_seen += 1
                    if files_seen > _TREE_MAX_FILES:
                        raise _TreeAuditFailure(
                            "max-files-exceeded", maximum=_TREE_MAX_FILES
                        )
                    if metadata.st_size > _TREE_MAX_FILE_BYTES:
                        raise _TreeAuditFailure(
                            "max-file-bytes-exceeded",
                            path=relative,
                            size_bytes=metadata.st_size,
                            maximum=_TREE_MAX_FILE_BYTES,
                        )
                    total_bytes += metadata.st_size
                    if total_bytes > _TREE_MAX_TOTAL_BYTES:
                        raise _TreeAuditFailure(
                            "max-total-bytes-exceeded", maximum=_TREE_MAX_TOTAL_BYTES
                        )
                    file_digest = _hash_regular_file_at(
                        directory_descriptor,
                        entry_name,
                        metadata,
                        relative,
                        deadline=deadline,
                        budget=budget,
                    )
                    records.append(
                        (relative, "file", metadata.st_mode & 0o777, file_digest)
                    )
                after = os.fstat(directory_descriptor)
                if not _same_file_snapshot(before, after):
                    raise _TreeAuditFailure(
                        "directory-changed-during-read", path=relative_directory
                    )
            finally:
                os.close(directory_descriptor)
            rebound = _open_tree_directory(
                root_descriptor,
                directory_parts,
                expected=before,
                relative=relative_directory,
                deadline=deadline,
            )
            os.close(rebound)
        root_after = os.fstat(root_descriptor)
        rebound_descriptor, root_rebound = _open_absolute_tree_root(root)
        os.close(rebound_descriptor)
        if not _same_file_snapshot(root_before, root_after) or not _same_file_snapshot(
            root_before, root_rebound
        ):
            raise _TreeAuditFailure("tree-root-changed-during-read")
    finally:
        os.close(root_descriptor)

    digest = hashlib.sha256()
    digest.update(b"learnfactory-tree-sha256-v2\0")
    for relative, kind, mode, file_digest in sorted(
        records, key=lambda item: item[0]
    ):
        relative_bytes = relative.encode("utf-8")
        if kind == "directory":
            digest.update(b"D")
            _hash_field(digest, relative_bytes)
            continue
        assert file_digest is not None
        digest.update(b"F")
        _hash_field(digest, relative_bytes)
        _hash_field(digest, mode.to_bytes(4, "big"))
        _hash_field(digest, file_digest)
    return _TreeSnapshot(
        checksum=digest.hexdigest(),
        entries=entries_seen,
        files=files_seen,
        total_bytes=total_bytes,
    )


def _hash_regular_file_at(
    directory_descriptor: int,
    name: str,
    expected: os.stat_result,
    relative: str,
    *,
    deadline: float | None = None,
    budget: _InvocationBudget | None = None,
) -> bytes:
    _check_deadline(deadline)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    try:
        descriptor = os.open(
            name,
            flags,
            dir_fd=directory_descriptor,
        )
    except OSError as error:
        raise _TreeAuditFailure(
            "unreadable-file", path=relative, error_type=error.__class__.__name__
        ) from error
    digest = hashlib.sha256()
    try:
        before = os.fstat(descriptor)
        if (
            not _same_file_snapshot(expected, before)
            or not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
        ):
            raise _TreeAuditFailure("file-changed-before-read", path=relative)
        read_bytes = 0
        while read_bytes < before.st_size:
            _check_deadline(deadline)
            expected_remaining = before.st_size - read_bytes
            read_size = (
                budget.next_read_size(expected_remaining, 1024 * 1024)
                if budget is not None
                else min(expected_remaining, 1024 * 1024)
            )
            chunk = os.read(descriptor, read_size)
            if not chunk:
                raise _TreeAuditFailure("file-changed-during-read", path=relative)
            if budget is not None:
                budget.consume_read(len(chunk))
            read_bytes += len(chunk)
            if read_bytes > _TREE_MAX_FILE_BYTES:
                raise _TreeAuditFailure(
                    "max-file-bytes-exceeded", path=relative, maximum=_TREE_MAX_FILE_BYTES
                )
            digest.update(chunk)
        after = os.fstat(descriptor)
        if read_bytes != expected.st_size or not _same_file_snapshot(before, after):
            raise _TreeAuditFailure("file-changed-during-read", path=relative)
    finally:
        os.close(descriptor)
    return digest.digest()


def _same_file_snapshot(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev,
        left.st_ino,
        left.st_mode,
        left.st_nlink,
        left.st_size,
        left.st_mtime_ns,
        left.st_ctime_ns,
    ) == (
        right.st_dev,
        right.st_ino,
        right.st_mode,
        right.st_nlink,
        right.st_size,
        right.st_mtime_ns,
        right.st_ctime_ns,
    )


def _hash_field(digest: Any, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _controller_evidence(
    db: Database,
    artifact: _ArtifactSnapshot,
    policy: _Policy,
    gate_status: str,
    gate_evidence: dict[str, Any],
    *,
    connection: sqlite3.Connection | None = None,
) -> tuple[dict[str, Any], bool]:
    query = """
        SELECT validation_id,status,evidence_json,claims_json
        FROM validations
        WHERE job_id=? AND attempt_number=? AND validator=?
        ORDER BY validation_id
        LIMIT ?
    """
    parameters = (
        artifact.job_id,
        artifact.artifact_attempt,
        policy.name,
        MAX_CONTROLLER_VALIDATIONS + 1,
    )
    if connection is None:
        with db.connect() as owned:
            rows = list(owned.execute(query, parameters))
    else:
        rows = list(connection.execute(query, parameters))

    summaries: list[dict[str, Any]] = []
    malformed: list[str] = []
    current: list[dict[str, Any]] = []
    legacy: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    conflict = False
    if len(rows) > MAX_CONTROLLER_VALIDATIONS:
        rows = rows[:MAX_CONTROLLER_VALIDATIONS]
        conflict = True
        malformed.append("controller-validation-row-limit-exceeded")

    expected_claims = (
        policy.specification.get("claims") if gate_status == "PASS" else []
    )
    expected_evidence_json = canonical_json(gate_evidence)
    for row in rows:
        validation_id = str(row["validation_id"])
        raw_evidence = str(row["evidence_json"])
        raw_claims = str(row["claims_json"])
        item: dict[str, Any] = {
            "validation_id": validation_id,
            "status": str(row["status"]),
            "evidence_sha256": _sha256_text(raw_evidence),
            "claims_sha256": _sha256_text(raw_claims),
        }
        if (
            len(raw_evidence.encode("utf-8")) > MAX_CONTROLLER_EVIDENCE_BYTES
            or len(raw_claims.encode("utf-8")) > MAX_CONTROLLER_EVIDENCE_BYTES
        ):
            malformed.append(validation_id)
            summaries.append({**item, "classification": "MALFORMED"})
            conflict = True
            continue
        try:
            evidence = _strict_json_object(raw_evidence)
            claims = _strict_json_array(raw_claims)
        except ValueError:
            malformed.append(validation_id)
            summaries.append({**item, "classification": "MALFORMED"})
            conflict = True
            continue
        item["claims"] = claims
        if any(str(claim).upper() in {"BUILDS", "TESTED"} for claim in claims):
            item["unsafe_semantic_claims"] = True
            conflict = True
        recorded_digest = evidence.get("policy_digest")
        if recorded_digest is None:
            item["classification"] = "LEGACY_UNBOUND"
            legacy.append(item)
        elif not isinstance(recorded_digest, str) or _SHA256.fullmatch(recorded_digest) is None:
            item["classification"] = "MALFORMED"
            malformed.append(validation_id)
            conflict = True
        elif recorded_digest != policy.digest:
            item["classification"] = "STALE_POLICY"
            item["policy_digest"] = recorded_digest
            stale.append(item)
        else:
            exact = (
                gate_status in {"PASS", "FAIL", "ERROR"}
                and item["status"] == gate_status
                and canonical_json(evidence) == expected_evidence_json
                and claims == expected_claims
            )
            item["classification"] = "FINAL_POLICY_MATCH" if exact else "FINAL_POLICY_CONFLICT"
            item["exact_replay_match"] = exact
            current.append(item)
            if not exact:
                conflict = True
        summaries.append(item)

    if conflict:
        category = "CONFLICT"
    elif current:
        category = "FINAL_POLICY_MATCH"
    elif legacy and not stale:
        category = "LEGACY_SCHEMA_ONLY"
    elif stale and not legacy:
        category = "STALE_POLICY_ONLY"
    elif stale or legacy:
        category = "MIXED_NONCURRENT"
    else:
        category = "ABSENT"
    result = {
        "category": category,
        "row_count": len(rows),
        "final_policy_count": len(current),
        "legacy_schema_count": len(legacy),
        "stale_policy_count": len(stale),
        "malformed_validation_ids": sorted(malformed),
        "rows": summaries,
    }
    return result, conflict


def _append_observation(
    db: Database,
    artifact: _ArtifactSnapshot,
    policy: _Policy,
    observation: dict[str, Any],
    *,
    deadline: float | None,
) -> dict[str, Any]:
    observation_json = canonical_json(observation)
    observation_sha256 = _sha256_text(observation_json)
    identity = {
        "artifact_id": artifact.artifact_id,
        "job_id": artifact.job_id,
        "artifact_attempt": artifact.artifact_attempt,
        "artifact_checksum": artifact.checksum,
        "checksum_algorithm": artifact.checksum_algorithm,
        "policy_name": policy.name,
        "policy_digest": policy.digest,
        "observation_sha256": observation_sha256,
    }
    audit_id = "byox_code_audit_v1_" + _sha256_json(identity)[:40]

    with db.transaction(immediate=True) as connection:
        current = connection.execute(
            """
            SELECT a.artifact_id,a.job_id,a.type AS artifact_type,a.path,a.checksum,
                   a.checksum_algorithm,a.integrity_status,
                   a.attempt_number AS artifact_attempt,
                   a.created_at AS artifact_created_at,
                   j.state AS job_state,j.attempt_count AS job_attempt_count,
                   j.payload_json
            FROM artifacts AS a JOIN jobs AS j ON j.job_id=a.job_id
            WHERE a.artifact_id=?
            """,
            (artifact.artifact_id,),
        ).fetchone()
        if current is None or _snapshot(current) != artifact:
            raise ByoxGateBackfillError(
                f"artifact or job changed during audit: {artifact.artifact_id}"
            )
        transactional_identity_errors = _identity_errors(
            db, artifact, connection=connection
        )
        if transactional_identity_errors != observation["identity_errors"]:
            raise ByoxGateBackfillError(
                f"artifact identity changed during audit: {artifact.artifact_id}"
            )
        controller, _ = _controller_evidence(
            db,
            artifact,
            policy,
            str(observation["gate"]["status"]),
            dict(observation["gate"]["evidence"]),
            connection=connection,
        )
        if _sha256_json(controller) != observation["controller_evidence_sha256"]:
            raise ByoxGateBackfillError(
                f"controller evidence changed during audit: {artifact.artifact_id}"
            )

        existing = connection.execute(
            """
            SELECT * FROM byox_code_presence_audits
            WHERE artifact_id=? AND policy_name=? AND policy_digest=?
              AND observation_sha256=?
            """,
            (artifact.artifact_id, policy.name, policy.digest, observation_sha256),
        ).fetchone()
        if existing is not None:
            _validate_existing_observation(existing, artifact, policy, observation)
            effective = _effective_outcome(connection, artifact.artifact_id, policy)
            _check_deadline(deadline)
            return {
                "audit_id": str(existing["audit_id"]),
                "artifact_id": artifact.artifact_id,
                "job_id": artifact.job_id,
                "artifact_attempt": artifact.artifact_attempt,
                "inserted": False,
                "observation_outcome": str(existing["outcome"]),
                "effective_outcome": effective,
                "controller_evidence_category": controller["category"],
            }

        prior = list(
            connection.execute(
                """
                SELECT audit_id,observation_sha256,policy_spec_sha256,outcome
                FROM byox_code_presence_audits
                WHERE artifact_id=? AND policy_name=? AND policy_digest=?
                ORDER BY audit_id
                LIMIT 52
                """,
                (artifact.artifact_id, policy.name, policy.digest),
            )
        )
        if len(prior) > 50:
            raise ByoxGateBackfillError(
                f"too many conflicting audit observations: {artifact.artifact_id}"
            )
        if any(row["policy_spec_sha256"] != policy.specification_sha256 for row in prior):
            raise ByoxGateBackfillError(
                f"current policy digest has conflicting specifications: {policy.digest}"
            )
        prior_ids = [str(row["audit_id"]) for row in prior]
        outcome = "CONFLICT" if prior_ids else str(observation["base_outcome"])
        evidence = {
            "schema_version": BYOX_CODE_AUDIT_SCHEMA_VERSION,
            "observation": observation,
            "ledger": {
                "conflicting_prior_audit_ids": prior_ids,
                "observation_count_after_insert": len(prior_ids) + 1,
                "effective_outcome": outcome,
            },
            "semantic_claims_added": [],
            "claims_builds_or_tested": False,
        }
        evidence_json = canonical_json(evidence)
        evidence_sha256 = _sha256_text(evidence_json)
        observed_checksum = observation["archive_tree"].get("observed_checksum")
        _check_deadline(deadline)
        connection.execute(
            """
            INSERT INTO byox_code_presence_audits(
                audit_id,artifact_id,job_id,artifact_attempt,artifact_type,
                artifact_path,artifact_checksum,checksum_algorithm,integrity_status,
                job_state,job_attempt_count,job_payload_sha256,
                policy_name,policy_digest,policy_spec_sha256,policy_spec_json,
                observation_sha256,outcome,gate_status,scope,semantic_claims_json,
                observed_checksum,controller_evidence_sha256,evidence_sha256,
                evidence_json,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                audit_id,
                artifact.artifact_id,
                artifact.job_id,
                artifact.artifact_attempt,
                artifact.artifact_type,
                artifact.path,
                artifact.checksum,
                artifact.checksum_algorithm,
                artifact.integrity_status,
                artifact.job_state,
                artifact.job_attempt_count,
                artifact.payload_sha256,
                policy.name,
                policy.digest,
                policy.specification_sha256,
                policy.specification_json,
                observation_sha256,
                outcome,
                observation["gate"]["status"],
                BYOX_CODE_AUDIT_SCOPE,
                "[]",
                observed_checksum,
                observation["controller_evidence_sha256"],
                evidence_sha256,
                evidence_json,
                now(),
            ),
        )
        effective = _effective_outcome(connection, artifact.artifact_id, policy)
        # The INSERT remains inside this transaction; expiry here rolls it back
        # rather than committing evidence after the invocation budget elapsed.
        _check_deadline(deadline)
    return {
        "audit_id": audit_id,
        "artifact_id": artifact.artifact_id,
        "job_id": artifact.job_id,
        "artifact_attempt": artifact.artifact_attempt,
        "inserted": True,
        "observation_outcome": outcome,
        "effective_outcome": effective,
        "controller_evidence_category": controller["category"],
    }


def _validate_existing_observation(
    row: sqlite3.Row,
    artifact: _ArtifactSnapshot,
    policy: _Policy,
    observation: dict[str, Any],
) -> None:
    if (
        row["job_id"] != artifact.job_id
        or row["artifact_attempt"] != artifact.artifact_attempt
        or row["artifact_checksum"] != artifact.checksum
        or row["checksum_algorithm"] != artifact.checksum_algorithm
        or row["policy_spec_sha256"] != policy.specification_sha256
        or row["policy_spec_json"] != policy.specification_json
        or row["scope"] != BYOX_CODE_AUDIT_SCOPE
        or row["semantic_claims_json"] != "[]"
        or _sha256_text(str(row["evidence_json"])) != row["evidence_sha256"]
    ):
        raise ByoxGateBackfillError(
            f"stored audit binding conflicts with current observation: {artifact.artifact_id}"
        )
    try:
        evidence = _strict_json_object(str(row["evidence_json"]))
    except ValueError as error:
        raise ByoxGateBackfillError(
            f"stored audit evidence is malformed: {artifact.artifact_id}"
        ) from error
    if evidence.get("observation") != observation:
        raise ByoxGateBackfillError(
            f"stored audit observation conflicts with replay: {artifact.artifact_id}"
        )


def _effective_outcome(
    connection: sqlite3.Connection, artifact_id: str, policy: _Policy
) -> str:
    rows = list(
        connection.execute(
            """
            SELECT observation_sha256,outcome
            FROM byox_code_presence_audits
            WHERE artifact_id=? AND policy_name=? AND policy_digest=?
            ORDER BY audit_id
            LIMIT 3
            """,
            (artifact_id, policy.name, policy.digest),
        )
    )
    if len(rows) != 1:
        return "CONFLICT"
    return str(rows[0]["outcome"])


def _assert_policy_ledger_consistency(db: Database, policy: _Policy) -> None:
    with db.connect() as connection:
        rows = list(
            connection.execute(
                """
                SELECT audit.*,
                       artifact.artifact_id AS bound_artifact_id,
                       artifact.job_id AS bound_job_id,
                       artifact.type AS bound_artifact_type,
                       artifact.path AS bound_artifact_path,
                       artifact.checksum AS bound_artifact_checksum,
                       artifact.checksum_algorithm AS bound_checksum_algorithm,
                       artifact.integrity_status AS bound_integrity_status,
                       artifact.attempt_number AS bound_artifact_attempt,
                       artifact.created_at AS bound_artifact_created_at,
                       job.state AS bound_job_state,
                       job.attempt_count AS bound_job_attempt_count,
                       job.payload_json AS bound_payload_json
                FROM byox_code_presence_audits AS audit
                LEFT JOIN artifacts AS artifact
                  ON artifact.artifact_id=audit.artifact_id
                LEFT JOIN jobs AS job ON job.job_id=audit.job_id
                WHERE audit.policy_name=? AND audit.policy_digest=?
                ORDER BY audit.artifact_id,audit.created_at,audit.audit_id
                LIMIT ?
                """,
                (policy.name, policy.digest, MAX_EXISTING_AUDIT_ROWS + 1),
            )
        )
        if len(rows) > MAX_EXISTING_AUDIT_ROWS:
            raise ByoxGateBackfillError("current-policy audit ledger exceeds safety bound")

        groups: dict[str, list[tuple[sqlite3.Row, dict[str, Any]]]] = {}
        for row in rows:
            audit_id = str(row["audit_id"])
            if (
                row["policy_spec_sha256"] != policy.specification_sha256
                or row["policy_spec_json"] != policy.specification_json
                or row["scope"] != BYOX_CODE_AUDIT_SCOPE
                or row["semantic_claims_json"] != "[]"
            ):
                raise ByoxGateBackfillError(
                    f"current-policy audit has conflicting policy scope: {audit_id}"
                )
            artifact_columns = (
                ("artifact_id", "bound_artifact_id"),
                ("job_id", "bound_job_id"),
                ("artifact_type", "bound_artifact_type"),
                ("artifact_path", "bound_artifact_path"),
                ("artifact_checksum", "bound_artifact_checksum"),
                ("checksum_algorithm", "bound_checksum_algorithm"),
                ("integrity_status", "bound_integrity_status"),
                ("artifact_attempt", "bound_artifact_attempt"),
                ("job_state", "bound_job_state"),
                ("job_attempt_count", "bound_job_attempt_count"),
            )
            if any(row[left] != row[right] for left, right in artifact_columns):
                raise ByoxGateBackfillError(
                    f"current-policy audit has stale artifact/job binding: {audit_id}"
                )
            raw_payload = row["bound_payload_json"]
            if (
                not isinstance(raw_payload, str)
                or _sha256_text(raw_payload) != row["job_payload_sha256"]
            ):
                raise ByoxGateBackfillError(
                    f"current-policy audit has conflicting payload binding: {audit_id}"
                )
            raw_evidence = str(row["evidence_json"])
            try:
                evidence = _strict_json_object(raw_evidence)
            except ValueError as error:
                raise ByoxGateBackfillError(
                    f"current-policy audit has malformed evidence: {audit_id}"
                ) from error
            if (
                canonical_json(evidence) != raw_evidence
                or _sha256_text(raw_evidence) != row["evidence_sha256"]
            ):
                raise ByoxGateBackfillError(
                    f"current-policy audit has incoherent evidence hash: {audit_id}"
                )
            observation = evidence.get("observation")
            ledger = evidence.get("ledger")
            if not isinstance(observation, dict) or not isinstance(ledger, dict):
                raise ByoxGateBackfillError(
                    f"current-policy audit lacks observation ledger: {audit_id}"
                )
            if _sha256_json(observation) != row["observation_sha256"]:
                raise ByoxGateBackfillError(
                    f"current-policy audit has incoherent observation hash: {audit_id}"
                )
            nested_artifact = observation.get("artifact")
            nested_policy = observation.get("policy")
            nested_gate = observation.get("gate")
            nested_tree = observation.get("archive_tree")
            nested_controller = observation.get("controller_evidence")
            if not all(
                isinstance(value, dict)
                for value in (
                    nested_artifact,
                    nested_policy,
                    nested_gate,
                    nested_tree,
                    nested_controller,
                )
            ):
                raise ByoxGateBackfillError(
                    f"current-policy audit evidence has invalid shape: {audit_id}"
                )
            expected_nested_artifact = {
                "artifact_id": row["artifact_id"],
                "job_id": row["job_id"],
                "artifact_type": row["artifact_type"],
                "artifact_attempt": row["artifact_attempt"],
                "artifact_checksum": row["artifact_checksum"],
                "checksum_algorithm": row["checksum_algorithm"],
                "integrity_status": row["integrity_status"],
                "job_state": row["job_state"],
                "job_attempt_count": row["job_attempt_count"],
                "job_payload_sha256": row["job_payload_sha256"],
            }
            if any(
                nested_artifact.get(key) != value
                for key, value in expected_nested_artifact.items()
            ):
                raise ByoxGateBackfillError(
                    f"current-policy audit has conflicting nested binding: {audit_id}"
                )
            if nested_policy != {
                "name": policy.name,
                "digest": policy.digest,
                "specification_sha256": policy.specification_sha256,
            }:
                raise ByoxGateBackfillError(
                    f"current-policy audit has conflicting nested policy: {audit_id}"
                )
            if (
                observation.get("schema_version") != BYOX_CODE_AUDIT_SCHEMA_VERSION
                or observation.get("audit_protocol") != BYOX_CODE_AUDIT_PROTOCOL
                or nested_tree.get("audit_protocol") != BYOX_CODE_AUDIT_PROTOCOL
                or observation.get("scope") != BYOX_CODE_AUDIT_SCOPE
                or observation.get("semantic_claims_added") != []
                or observation.get("claims_builds_or_tested") is not False
                or evidence.get("semantic_claims_added") != []
                or evidence.get("claims_builds_or_tested") is not False
                or nested_gate.get("status") != row["gate_status"]
                or nested_tree.get("observed_checksum") != row["observed_checksum"]
                or _sha256_json(nested_controller) != row["controller_evidence_sha256"]
                or observation.get("controller_evidence_sha256")
                != row["controller_evidence_sha256"]
            ):
                raise ByoxGateBackfillError(
                    f"current-policy audit has conflicting evidence fields: {audit_id}"
                )
            immutable_snapshot_bound = (
                nested_tree.get("status") == "CHECKED"
                and nested_tree.get("source_hash_passes") == 3
                and nested_tree.get("snapshot_hash_passes") == 2
                and nested_tree.get("snapshot_checksum") == row["artifact_checksum"]
                and nested_tree.get("post_gate_snapshot_checksum")
                == row["artifact_checksum"]
                and nested_tree.get("observed_checksum") == row["artifact_checksum"]
                and nested_tree.get("manifest_tree_checksum")
                == row["artifact_checksum"]
                and isinstance(nested_tree.get("manifest_digest"), str)
                and _SHA256.fullmatch(str(nested_tree.get("manifest_digest")))
                is not None
                and isinstance(nested_tree.get("policy_manifest_digest"), str)
                and _SHA256.fullmatch(
                    str(nested_tree.get("policy_manifest_digest"))
                )
                is not None
                and isinstance(nested_gate.get("evidence"), dict)
                and nested_gate["evidence"].get("manifest_digest")
                == nested_tree.get("policy_manifest_digest")
                and nested_tree.get("matches_stored_checksum") is True
            )
            if (
                nested_gate.get("status") != "NOT_RUN"
                and nested_tree.get("status") == "CHECKED"
                and not immutable_snapshot_bound
            ) or (
                observation.get("base_outcome") == "PASS"
                and not immutable_snapshot_bound
            ):
                raise ByoxGateBackfillError(
                    f"current-policy audit lacks immutable snapshot binding: {audit_id}"
                )
            reason_codes = observation.get("reason_codes")
            identity_errors = observation.get("identity_errors")
            if (
                not isinstance(reason_codes, list)
                or not all(isinstance(value, str) for value in reason_codes)
                or reason_codes != sorted(set(reason_codes))
                or not isinstance(identity_errors, list)
                or not all(isinstance(value, str) for value in identity_errors)
                or identity_errors != sorted(set(identity_errors))
                or observation.get("base_outcome") != _expected_base_outcome(observation)
            ):
                raise ByoxGateBackfillError(
                    f"current-policy audit has incoherent outcome evidence: {audit_id}"
                )
            snapshot = _ArtifactSnapshot(
                artifact_id=str(row["bound_artifact_id"]),
                job_id=str(row["bound_job_id"]),
                artifact_type=str(row["bound_artifact_type"]),
                path=str(row["bound_artifact_path"]),
                checksum=str(row["bound_artifact_checksum"]),
                checksum_algorithm=str(row["bound_checksum_algorithm"]),
                integrity_status=str(row["bound_integrity_status"]),
                artifact_attempt=int(row["bound_artifact_attempt"]),
                artifact_created_at=float(row["bound_artifact_created_at"]),
                job_state=str(row["bound_job_state"]),
                job_attempt_count=int(row["bound_job_attempt_count"]),
                payload_json=raw_payload,
                payload_sha256=str(row["job_payload_sha256"]),
            )
            controller, _ = _controller_evidence(
                db,
                snapshot,
                policy,
                str(nested_gate["status"]),
                dict(nested_gate.get("evidence", {})),
                connection=connection,
            )
            if controller != nested_controller:
                raise ByoxGateBackfillError(
                    f"current-policy audit has stale controller evidence: {audit_id}"
                )
            identity = {
                "artifact_id": row["artifact_id"],
                "job_id": row["job_id"],
                "artifact_attempt": row["artifact_attempt"],
                "artifact_checksum": row["artifact_checksum"],
                "checksum_algorithm": row["checksum_algorithm"],
                "policy_name": policy.name,
                "policy_digest": policy.digest,
                "observation_sha256": row["observation_sha256"],
            }
            if audit_id != "byox_code_audit_v1_" + _sha256_json(identity)[:40]:
                raise ByoxGateBackfillError(
                    f"current-policy audit has incoherent identity: {audit_id}"
                )
            groups.setdefault(str(row["artifact_id"]), []).append((row, evidence))

        for artifact_id, records in groups.items():
            group_ids = {str(row["audit_id"]) for row, _ in records}
            roots = 0
            for row, evidence in records:
                ledger = evidence["ledger"]
                prior = ledger.get("conflicting_prior_audit_ids")
                if (
                    not isinstance(prior, list)
                    or not all(isinstance(value, str) for value in prior)
                    or len(set(prior)) != len(prior)
                    or not set(prior) <= group_ids - {str(row["audit_id"])}
                    or ledger.get("observation_count_after_insert") != len(prior) + 1
                ):
                    raise ByoxGateBackfillError(
                        f"current-policy audit has incoherent conflict chain: {artifact_id}"
                    )
                if prior:
                    if row["outcome"] != "CONFLICT" or ledger.get("effective_outcome") != "CONFLICT":
                        raise ByoxGateBackfillError(
                            f"current-policy audit fails closed incorrectly: {artifact_id}"
                        )
                else:
                    roots += 1
                    if (
                        row["outcome"] != evidence["observation"]["base_outcome"]
                        or ledger.get("effective_outcome") != row["outcome"]
                    ):
                        raise ByoxGateBackfillError(
                            f"current-policy audit root outcome is incoherent: {artifact_id}"
                        )
            if roots != 1 or (len(records) > 1 and not any(record[0]["outcome"] == "CONFLICT" for record in records)):
                raise ByoxGateBackfillError(
                    f"current-policy audit observations conflict ambiguously: {artifact_id}"
                )


def _expected_base_outcome(observation: dict[str, Any]) -> str:
    controller = observation.get("controller_evidence")
    gate = observation.get("gate")
    tree = observation.get("archive_tree")
    reasons = observation.get("reason_codes")
    if isinstance(controller, dict) and controller.get("category") == "CONFLICT":
        return "CONFLICT"
    if (
        isinstance(gate, dict)
        and gate.get("status") == "ERROR"
        or isinstance(tree, dict)
        and tree.get("status") == "ERROR"
    ):
        return "ERROR"
    if reasons or not isinstance(gate, dict) or gate.get("status") != "PASS":
        return "FAIL"
    return "PASS"


def _remaining_unaudited(db: Database, policy: _Policy) -> int:
    with db.connect() as connection:
        return int(
            connection.execute(
                f"""
                SELECT COUNT(*) FROM artifacts AS artifact
                WHERE artifact.type IN ({','.join('?' for _ in _ARTIFACT_POLICIES)})
                  AND NOT EXISTS (
                      SELECT 1 FROM byox_code_presence_audits AS audit
                      WHERE audit.artifact_id=artifact.artifact_id
                        AND audit.policy_name=? AND audit.policy_digest=?
                  )
                """,
                (*_ARTIFACT_POLICIES, policy.name, policy.digest),
            ).fetchone()[0]
        )


def _strict_json_object(raw: str) -> dict[str, Any]:
    value = _strict_json(raw)
    if not isinstance(value, dict):
        raise ValueError("JSON value is not an object")
    return value


def _strict_json_array(raw: str) -> list[Any]:
    value = _strict_json(raw)
    if not isinstance(value, list):
        raise ValueError("JSON value is not an array")
    return value


def _strict_json(raw: str) -> Any:
    try:
        return json.loads(
            raw,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-standard JSON number: {token}")
            ),
        )
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("invalid JSON") from error


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_text(canonical_json(value))
