from __future__ import annotations

import argparse
import contextlib
import hashlib
import math
import os
import re
import signal
import socket
import sqlite3
import sys
import threading
import time
import traceback
from collections.abc import Callable, Iterator
from pathlib import Path

from .config import load_settings
from .db import Database
from .handlers import HandlerFailure, JobHandlers
from .jobs import (
    ClaimedJob,
    JobError,
    JobRepository,
    JobState,
    PublicationCallbackError,
    UnsatisfiedDependencyError,
)
from .run_provenance import (
    capture_run_provenance,
    unavailable_run_provenance,
    write_run_provenance,
)
from .result_channel import fresh_result_channel, worker_result_transport_root
from .util import canonical_json, new_id, now, redact, repository_revision, tree_sha256
from .validation import ValidationResult, Validator
from .workspace import PreparedArtifact, WorkspaceError, WorkspaceManager


class _WorkerBoundaryStop(RuntimeError):
    def __init__(self, exit_code: int) -> None:
        super().__init__(f"worker stopped at publication boundary ({exit_code})")
        self.exit_code = exit_code


class _HeartbeatPublicationGate:
    """Serialize local lease cancellation with final publication."""

    def __init__(self, cancel_event: threading.Event) -> None:
        self.cancel_event = cancel_event
        self._condition = threading.Condition()
        self._stop_requested = False
        self._publication_active = False

    def wait(self, timeout: float) -> bool:
        with self._condition:
            self._condition.wait_for(
                lambda: self._stop_requested or self.cancel_event.is_set(),
                timeout=max(0.0, timeout),
            )
            return self._stop_requested or self.cancel_event.is_set()

    def request_local_cancel(self) -> None:
        with self._condition:
            self.cancel_event.set()
            self._condition.notify_all()

    def request_supervisor_cancel(
        self, supervisor_stop_event: threading.Event
    ) -> None:
        """Publish the supervisor cause and its shared cancellation atomically."""

        with self._condition:
            supervisor_stop_event.set()
            self.cancel_event.set()
            self._condition.notify_all()

    def stop_cause(self, supervisor_stop_event: threading.Event) -> str | None:
        """Classify a stop at one linearization point.

        The second supervisor read is intentional: SIGTERM may arrive after
        the first read but while the shared cancellation event is observed.
        Signal delivery uses this same condition, so either the local cause or
        the supervisor cause wins coherently rather than reporting exit 6 for
        an already-delivered controller interruption.
        """

        with self._condition:
            if supervisor_stop_event.is_set():
                return "supervisor"
            if self.cancel_event.is_set():
                return (
                    "supervisor"
                    if supervisor_stop_event.is_set()
                    else "local"
                )
            return None

    def request_stop(self) -> None:
        with self._condition:
            self._stop_requested = True
            self._condition.notify_all()

    def stop_requested(self) -> bool:
        with self._condition:
            return self._stop_requested

    @contextlib.contextmanager
    def publication(self) -> Iterator[None]:
        with self._condition:
            if not self._stop_requested:
                raise RuntimeError("heartbeat must be stopped before publication")
            if self._publication_active:
                raise RuntimeError("publication gate is already active")
            self._publication_active = True
            try:
                yield
            finally:
                self._publication_active = False


@contextlib.contextmanager
def _quiesced_heartbeat_publication(
    gate: _HeartbeatPublicationGate,
    heartbeat: threading.Thread,
) -> Iterator[None]:
    gate.request_stop()
    heartbeat.join()
    if heartbeat.is_alive():
        raise RuntimeError("heartbeat did not quiesce before publication")
    with gate.publication():
        yield


def _fence_worker_boundary(
    jobs: JobRepository,
    *,
    job_id: str,
    owner: str,
    lease_token: str,
    worker_id: str,
    stop_gate: _HeartbeatPublicationGate,
    supervisor_stop_event: threading.Event,
    boundary: str,
) -> None:
    """Reconcile durable, supervisor, and local stop causes in that order."""

    if jobs.cancellation_requested(job_id):
        jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
        raise _WorkerBoundaryStop(130)
    stop_cause = stop_gate.stop_cause(supervisor_stop_event)
    if stop_cause == "supervisor":
        interrupted_state = jobs.interrupt(
            job_id,
            owner,
            lease_token,
            worker_id,
            reason=f"worker stopped by controller {boundary}",
        )
        raise _WorkerBoundaryStop(
            130 if interrupted_state is JobState.CANCELLED else 143
        )
    if stop_cause == "local":
        try:
            interrupted_state = jobs.fail(
                job_id,
                owner,
                lease_token,
                worker_id,
                kind="worker_interrupted",
                error=f"local lease or heartbeat cancellation {boundary}",
                retryable=True,
            )
        except JobError:
            # Scheduler recovery may already own an expired lease. Either way,
            # publication is fenced and this process must stop useful work.
            interrupted_state = None
        raise _WorkerBoundaryStop(
            130 if interrupted_state is JobState.CANCELLED else 6
        )


def run_worker(job_id: str, owner: str, lease_token: str, config_path: Path | None = None) -> int:
    settings = load_settings(config_path)
    db = Database(
        settings.database,
        settings.migrations,
        busy_timeout_seconds=settings.database_busy_timeout_seconds,
    )
    jobs = JobRepository(db, retry_base=settings.retry_base_seconds, retry_max=settings.retry_max_seconds)
    record = jobs.get(job_id)
    if (
        record is None
        or record["state"] != "CLAIMED"
        or record["owner"] != owner
        or record["lease_token"] != lease_token
    ):
        return 2
    job = ClaimedJob(
        job_id=job_id,
        type=record["type"],
        worker_type=record["worker_type"],
        payload=record["payload"],
        attempt_count=record["attempt_count"],
        workspace=record["workspace"],
        model=record["model"],
        reasoning_effort=record["reasoning_effort"],
        lease_token=lease_token,
    )
    manager = WorkspaceManager(settings.warehouse, db)
    manager.initialize()
    try:
        workspace = manager.allocate(job_id, job.attempt_count)
    except Exception as error:
        jobs.fail(job_id, owner, lease_token, None, kind="workspace_failure", error=str(error), retryable=True)
        return 3
    log_dir = settings.warehouse / "logs" / job_id / f"attempt-{job.attempt_count:03d}"
    log_dir.mkdir(parents=True, exist_ok=True)
    worker_id = new_id("worker")
    run_id = new_id("run")
    # This nonce is an ephemeral capability independent of every durable ID.
    # It is passed only to the runtime handler/backend and is never provenance.
    result_channel = fresh_result_channel(
        worker_result_transport_root(
            settings.warehouse,
            job_id=job_id,
            attempt_number=job.attempt_count,
        )
    )
    effective_model = job.model or settings.backend.model
    effective_reasoning = job.reasoning_effort or settings.backend.reasoning_effort
    cancel_event = threading.Event()
    supervisor_stop_event = threading.Event()
    heartbeat_gate = _HeartbeatPublicationGate(cancel_event)

    with db.connect() as connection:
        dependency_job_ids = [
            str(row["depends_on_job_id"])
            for row in connection.execute(
                """
                SELECT depends_on_job_id FROM job_dependencies
                WHERE job_id=? ORDER BY depends_on_job_id
                """,
                (job_id,),
            )
        ]
    try:
        run_provenance = capture_run_provenance(
            settings,
            job_id=job_id,
            job_type=job.type,
            worker_type=job.worker_type,
            payload=job.payload,
            dependency_job_ids=dependency_job_ids,
            workspace=workspace,
            log_dir=log_dir,
            effective_model=effective_model,
            effective_reasoning=effective_reasoning,
        )
    except Exception as error:
        run_provenance = unavailable_run_provenance(error)
    try:
        run_provenance_path: Path | None = write_run_provenance(
            log_dir, run_provenance
        )
    except (OSError, TypeError, ValueError) as error:
        run_provenance_path = None
        run_provenance.metadata["human_record"] = {
            "status": "WRITE_FAILED",
            "error": redact(str(error), 500),
        }

    def request_stop(signum: int, frame: object) -> None:
        heartbeat_gate.request_supervisor_cancel(supervisor_stop_event)

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    with db.transaction(immediate=True) as connection:
        connection.execute(
            """
            INSERT INTO workers(
                worker_id,type,process_id,workspace,state,started_at,last_activity,current_job,hostname
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (worker_id, job.worker_type, os.getpid(), str(workspace), "STARTING", now(), now(), job_id, socket.gethostname()),
        )
        connection.execute(
            """
            INSERT INTO job_runs(
                run_id,job_id,worker_id,attempt_number,backend,model,reasoning_effort,
                process_id,started_at,stdout_path,stderr_path,provider,base_url,
                wire_api,supports_websockets,reproducibility_digest,
                reproducibility_path,reproducibility_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                run_id, job_id, worker_id, job.attempt_count,
                settings.backend.name if job.type == "codex_task" else "pending",
                effective_model,
                effective_reasoning, os.getpid(), now(),
                str(log_dir / "worker.stdout.log"), str(log_dir / "worker.stderr.log"),
                settings.backend.provider if job.type == "codex_task" else None,
                settings.backend.base_url if job.type == "codex_task" else None,
                "responses" if job.type == "codex_task" else None,
                int(settings.backend.supports_websockets)
                if job.type == "codex_task"
                else None,
                run_provenance.digest,
                str(run_provenance_path) if run_provenance_path is not None else None,
                canonical_json(run_provenance.metadata),
            ),
        )
        db.emit_event(
            "worker",
            "RUN_REPRODUCIBILITY_CAPTURED",
            job_id=job_id,
            worker_id=worker_id,
            payload={
                "run_id": run_id,
                "digest": run_provenance.digest,
                "path": (
                    str(run_provenance_path)
                    if run_provenance_path is not None
                    else None
                ),
                "repository_status": run_provenance.metadata.get(
                    "repository", {}
                ).get("status"),
            },
            connection=connection,
        )
    try:
        initial_lease_expires_at = jobs.start(
            job_id,
            owner,
            lease_token,
            worker_id,
            str(workspace),
            lease_seconds=settings.lease_seconds,
        )
    except Exception as error:
        if jobs.cancellation_requested(job_id):
            try:
                jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
            except JobError:
                # An expired or replaced lease belongs to scheduler recovery.
                pass
        _finish_worker(db, worker_id, "FAILED", str(error))
        return 4

    heartbeat = threading.Thread(
        target=_heartbeat_loop,
        args=(
            jobs,
            job_id,
            owner,
            lease_token,
            worker_id,
            settings.lease_seconds,
            settings.heartbeat_seconds,
            initial_lease_expires_at,
            settings.database_busy_timeout_seconds,
            cancel_event,
        ),
        kwargs={"_publication_gate": heartbeat_gate},
        daemon=True,
        name=f"heartbeat-{job_id}",
    )
    heartbeat.start()
    exit_code = 1
    prepared: PreparedArtifact | None = None
    archive_projection: Path | None = None
    try:
        result = JobHandlers(
            settings,
            db,
            manager,
            result_channel=result_channel,
        ).execute(job, workspace, log_dir, cancel_event)
        _fence_worker_boundary(
            jobs,
            job_id=job_id,
            owner=owner,
            lease_token=lease_token,
            worker_id=worker_id,
            stop_gate=heartbeat_gate,
            supervisor_stop_event=supervisor_stop_event,
            boundary="after handler execution",
        )
        _enforce_validator_execution_policy(
            result.validators,
            allow_host_commands=settings.allow_host_command_validators,
        )
        authoritative_cutover_contract = _validated_byox_cutover_contract(
            result.validators,
            result.archive_paths,
            result.metadata,
        )
        with db.transaction(immediate=True) as connection:
            connection.execute(
                """
                UPDATE job_runs SET backend=?,session_id=?,usage_json=? WHERE run_id=?
                """,
                (
                    result.backend_name,
                    result.backend_result.session_id if result.backend_result else None,
                    canonical_json(result.backend_result.usage if result.backend_result else {}),
                    run_id,
                ),
            )
        if jobs.cancellation_requested(job_id):
            jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
            exit_code = 130
        elif supervisor_stop_event.is_set():
            interrupted_state = jobs.interrupt(
                job_id, owner, lease_token, worker_id,
                reason="worker stopped by controller during handler execution",
            )
            exit_code = 130 if interrupted_state is JobState.CANCELLED else 143
        else:
            validations = Validator(db).run(
                job_id,
                workspace,
                result.validators,
                log_dir,
                attempt_number=job.attempt_count,
                cancel_event=cancel_event,
            )
            _fence_worker_boundary(
                jobs,
                job_id=job_id,
                owner=owner,
                lease_token=lease_token,
                worker_id=worker_id,
                stop_gate=heartbeat_gate,
                supervisor_stop_event=supervisor_stop_event,
                boundary="after validation",
            )
            if jobs.cancellation_requested(job_id):
                jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
                exit_code = 130
            elif supervisor_stop_event.is_set():
                interrupted_state = jobs.interrupt(
                    job_id, owner, lease_token, worker_id,
                    reason="worker stopped by controller during validation",
                )
                exit_code = (
                    130 if interrupted_state is JobState.CANCELLED else 143
                )
            elif not validations or not all(item.passed for item in validations):
                evidence = "; ".join(
                    f"{item.name}={item.status}:{item.evidence}" for item in validations
                )
                jobs.fail(
                    job_id, owner, lease_token, worker_id, kind="validation_failure", error=evidence,
                    retryable=bool(job.payload.get("retry_validation", False)),
                )
                exit_code = 5
            else:
                validation_labels = _validation_labels(validations)
                validation_workspace_tree_sha256 = tree_sha256(workspace)
                if (
                    authoritative_cutover_contract is not None
                    and validation_workspace_tree_sha256
                    != authoritative_cutover_contract[0]
                ):
                    raise HandlerFailure(
                        "authoritative validation snapshot changed during validation",
                        kind="validation_failure",
                        retryable=bool(job.payload.get("retry_validation", False)),
                    )
                archive_candidate = workspace
                if result.archive_paths is not None:
                    try:
                        archive_projection = manager.create_archive_projection(
                            workspace, result.archive_paths
                        )
                    except WorkspaceError as error:
                        raise HandlerFailure(
                            f"unsafe or incomplete projected output: {error}",
                            kind="validation_failure",
                            retryable=bool(job.payload.get("retry_validation", False)),
                        ) from error
                    archive_candidate = archive_projection
                validated_tree_sha256 = tree_sha256(archive_candidate)
                if (
                    authoritative_cutover_contract is not None
                    and validated_tree_sha256
                    != authoritative_cutover_contract[1]
                ):
                    raise HandlerFailure(
                        "authoritative validation archive candidate changed before archive",
                        kind="validation_failure",
                        retryable=bool(job.payload.get("retry_validation", False)),
                    )
                prepared = manager.prepare_archive(
                    job_id,
                    job.attempt_count,
                    archive_candidate,
                    artifact_type=result.artifact_type,
                    semantic_path=result.semantic_path,
                    metadata={
                        **result.metadata,
                        "job_id": job_id,
                        "run_id": run_id,
                        "attempt": job.attempt_count,
                        "factory_revision": repository_revision(settings.root),
                        "run_reproducibility": {
                            "schema": run_provenance.metadata.get("schema"),
                            "digest": run_provenance.digest,
                            "record_path": (
                                str(run_provenance_path)
                                if run_provenance_path is not None
                                else None
                            ),
                        },
                        "archive_projection": (
                            {
                                "schema_version": 1,
                                "mode": "declared-worker-outputs",
                                "paths": list(result.archive_paths),
                                "staged_inputs_excluded": True,
                                "source_workspace_checksum_algorithm": "tree-sha256-v2",
                                "source_workspace_checksum": validation_workspace_tree_sha256,
                                "projected_tree_checksum_algorithm": "tree-sha256-v2",
                                "projected_tree_checksum": validated_tree_sha256,
                            }
                            if result.archive_paths is not None
                            else {
                                "schema_version": 1,
                                "mode": "complete-workspace",
                                "source_workspace_checksum_algorithm": "tree-sha256-v2",
                                "source_workspace_checksum": validation_workspace_tree_sha256,
                            }
                        ),
                        "validation_evidence": [
                            {"validator": item.name, "status": item.status, "evidence": item.evidence}
                            for item in validations
                        ],
                        "validation_labels": validation_labels,
                        "validation_workspace_tree_sha256": validation_workspace_tree_sha256,
                        "validated_tree_sha256": validated_tree_sha256,
                    },
                    validation_status="+".join(validation_labels),
                    validation_labels=validation_labels,
                )
                _fence_worker_boundary(
                    jobs,
                    job_id=job_id,
                    owner=owner,
                    lease_token=lease_token,
                    worker_id=worker_id,
                    stop_gate=heartbeat_gate,
                    supervisor_stop_event=supervisor_stop_event,
                    boundary="after artifact preparation",
                )
                if prepared.checksum != validated_tree_sha256:
                    raise JobError("candidate changed between validation and archive preparation")
                # Projection and durable preparation can be non-trivial for a
                # large output. Reconcile stop/cancel state again at the final
                # publication boundary rather than promoting work after an
                # operator requested shutdown during that interval.
                if jobs.cancellation_requested(job_id):
                    jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
                    exit_code = 130
                elif supervisor_stop_event.is_set():
                    interrupted_state = jobs.interrupt(
                        job_id,
                        owner,
                        lease_token,
                        worker_id,
                        reason="worker stopped by controller during artifact preparation",
                    )
                    exit_code = (
                        130 if interrupted_state is JobState.CANCELLED else 143
                    )
                else:
                    with _quiesced_heartbeat_publication(
                        heartbeat_gate,
                        heartbeat,
                    ):
                        _fence_worker_boundary(
                            jobs,
                            job_id=job_id,
                            owner=owner,
                            lease_token=lease_token,
                            worker_id=worker_id,
                            stop_gate=heartbeat_gate,
                            supervisor_stop_event=supervisor_stop_event,
                            boundary="immediately before success publication",
                        )
                        # This return from the final fence is the local-stop
                        # linearization point. The heartbeat and watchdog are
                        # joined, so they cannot revoke authority afterward.
                        # A later SIGTERM does not undo publication already in
                        # progress; durable operator cancellation still wins
                        # because succeed_with_artifact rechecks it in SQLite.
                        jobs.succeed_with_artifact(
                            job_id,
                            owner,
                            lease_token,
                            worker_id,
                            prepared,
                            on_publish=result.on_publish,
                            publication_scope=result.publication_scope,
                        )
                    prepared = None
                    if result.on_commit is not None:
                        try:
                            result.on_commit()
                        except Exception as error:
                            # The artifact and learner rows are already committed. A
                            # human-readable learner directory is a rebuildable view,
                            # so never attempt an impossible rollback or rewrite the
                            # succeeded job as failed after this boundary.
                            db.emit_event(
                                "worker",
                                "POST_COMMIT_SYNC_FAILED",
                                job_id=job_id,
                                worker_id=worker_id,
                                payload={"error": redact(str(error))},
                            )
                    exit_code = 0
    except _WorkerBoundaryStop as stopped:
        exit_code = stopped.exit_code
    except PublicationCallbackError as error:
        if jobs.cancellation_requested(job_id):
            jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
            exit_code = 130
        else:
            stop_cause = heartbeat_gate.stop_cause(supervisor_stop_event)
            if stop_cause == "supervisor":
                interrupted_state = jobs.interrupt(
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    reason="worker stopped by controller at publication callback fence",
                )
                exit_code = (
                    130 if interrupted_state is JobState.CANCELLED else 143
                )
            elif stop_cause == "local":
                try:
                    interrupted_state = jobs.fail(
                        job_id,
                        owner,
                        lease_token,
                        worker_id,
                        kind="worker_interrupted",
                        error="local lease or heartbeat cancellation at publication callback fence",
                        retryable=True,
                    )
                except JobError:
                    interrupted_state = None
                exit_code = (
                    130 if interrupted_state is JobState.CANCELLED else 6
                )
            else:
                jobs.fail(
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    kind="publication_failure",
                    error=str(error),
                    retryable=False,
                )
                exit_code = 6
    except UnsatisfiedDependencyError as error:
        if jobs.cancellation_requested(job_id):
            jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
            exit_code = 130
        else:
            stop_cause = heartbeat_gate.stop_cause(supervisor_stop_event)
            if stop_cause == "supervisor":
                interrupted_state = jobs.interrupt(
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    reason="worker stopped by controller at dependency publication fence",
                )
                exit_code = (
                    130 if interrupted_state is JobState.CANCELLED else 143
                )
            elif stop_cause == "local":
                try:
                    interrupted_state = jobs.fail(
                        job_id,
                        owner,
                        lease_token,
                        worker_id,
                        kind="worker_interrupted",
                        error="local lease or heartbeat cancellation at dependency publication fence",
                        retryable=True,
                    )
                except JobError:
                    interrupted_state = None
                exit_code = (
                    130 if interrupted_state is JobState.CANCELLED else 6
                )
            else:
                # Publication rolled back atomically, including its artifact
                # and optional on_publish rows. A blocked-dependency job can be
                # promoted again if its prerequisites recover.
                jobs.block(
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    kind="blocked_dependency",
                    error=str(error),
                )
                exit_code = 8
    except HandlerFailure as error:
        if jobs.cancellation_requested(job_id):
            jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
            exit_code = 130
        else:
            stop_cause = heartbeat_gate.stop_cause(supervisor_stop_event)
            if stop_cause == "supervisor":
                interrupted_state = jobs.interrupt(
                    job_id, owner, lease_token, worker_id,
                    reason=f"worker stopped by controller: {error}",
                )
                exit_code = (
                    130 if interrupted_state is JobState.CANCELLED else 143
                )
            elif error.kind == "cancelled" or stop_cause == "local":
                interrupted_state = jobs.fail(
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    kind="worker_interrupted",
                    error=str(error),
                    retryable=True,
                )
                exit_code = (
                    130 if interrupted_state is JobState.CANCELLED else 6
                )
            elif error.kind.startswith("blocked_"):
                jobs.block(
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    kind=error.kind,
                    error=str(error),
                )
                exit_code = 8
            else:
                jobs.fail(
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    kind=error.kind,
                    error=str(error),
                    retryable=error.retryable,
                )
                exit_code = 6
    except Exception as error:
        detail = f"{type(error).__name__}: {error}\n{traceback.format_exc()}"
        try:
            if jobs.cancellation_requested(job_id):
                jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
                exit_code = 130
            else:
                stop_cause = heartbeat_gate.stop_cause(supervisor_stop_event)
                if stop_cause == "supervisor":
                    interrupted_state = jobs.interrupt(
                        job_id,
                        owner,
                        lease_token,
                        worker_id,
                        reason="worker stopped by controller after internal error",
                    )
                    exit_code = (
                        130 if interrupted_state is JobState.CANCELLED else 143
                    )
                elif stop_cause == "local":
                    try:
                        interrupted_state = jobs.fail(
                            job_id,
                            owner,
                            lease_token,
                            worker_id,
                            kind="worker_interrupted",
                            error="local lease or heartbeat cancellation after internal error",
                            retryable=True,
                        )
                    except JobError:
                        interrupted_state = None
                    exit_code = (
                        130 if interrupted_state is JobState.CANCELLED else 6
                    )
                else:
                    jobs.fail(
                        job_id,
                        owner,
                        lease_token,
                        worker_id,
                        kind="worker_crash",
                        error=detail,
                        retryable=True,
                    )
        except JobError:
            pass
        if exit_code not in (6, 130, 143):
            exit_code = 7
    finally:
        if prepared is not None:
            try:
                manager.discard_prepared(prepared)
            except Exception:
                pass
        if archive_projection is not None:
            try:
                manager.discard_archive_projection(archive_projection)
            except Exception:
                pass
        heartbeat_gate.request_stop()
        cancel_event.set()
        heartbeat.join()
        state = "SUCCEEDED" if exit_code == 0 else "CANCELLED" if exit_code == 130 else "INTERRUPTED" if exit_code == 143 else "FAILED"
        _finish_worker(db, worker_id, state, None if exit_code == 0 else f"exit {exit_code}")
        with db.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE job_runs SET finished_at=?,exit_code=? WHERE run_id=?",
                (now(), exit_code, run_id),
            )
    return exit_code


def _lease_safety_lead(heartbeat_seconds: float) -> float:
    return max(0.01, min(0.25, heartbeat_seconds))


class _LeaseDeadline:
    """Thread-safe monotonic view of the last durably confirmed lease."""

    def __init__(
        self,
        lease_expires_at: float,
        *,
        monotonic_clock: Callable[[], float],
        wall_clock: Callable[[], float],
    ) -> None:
        if (
            isinstance(lease_expires_at, bool)
            or not isinstance(lease_expires_at, (int, float))
            or not math.isfinite(float(lease_expires_at))
        ):
            raise ValueError("invalid durable lease expiry")
        self._monotonic_clock = monotonic_clock
        self._wall_clock = wall_clock
        current = monotonic_clock()
        self._deadline = current + max(
            0.0, float(lease_expires_at) - wall_clock()
        )
        self._condition = threading.Condition()
        self._stopped = False
        self._risk_fired = False

    def current(self) -> float:
        with self._condition:
            return self._deadline

    def renew(self, lease_expires_at: float, *, observed_at: float) -> bool:
        if (
            isinstance(lease_expires_at, bool)
            or not isinstance(lease_expires_at, (int, float))
            or not math.isfinite(float(lease_expires_at))
        ):
            return False
        proposed = observed_at + max(
            0.0, float(lease_expires_at) - self._wall_clock()
        )
        with self._condition:
            # A renewal observed after the prior durable horizon cannot undo a
            # watchdog decision, even if SQLite committed it late.
            if (
                self._stopped
                or self._risk_fired
                or observed_at >= self._deadline
                or proposed <= observed_at
            ):
                return False
            self._deadline = proposed
            self._condition.notify_all()
            return True

    def stop(self) -> None:
        with self._condition:
            self._stopped = True
            self._condition.notify_all()

    def watch(
        self,
        cancel_event: threading.Event,
        *,
        request_cancel: Callable[[], None] | None = None,
        safety_lead: float,
        job_id: str,
        worker_id: str,
    ) -> None:
        seconds_until_expiry = 0.0
        with self._condition:
            while not self._stopped and not cancel_event.is_set():
                seconds_until_expiry = (
                    self._deadline - self._monotonic_clock()
                )
                wait_seconds = seconds_until_expiry - safety_lead
                if wait_seconds <= 0:
                    self._risk_fired = True
                    break
                self._condition.wait(timeout=wait_seconds)
            if self._stopped or cancel_event.is_set():
                return
        _heartbeat_diagnostic(
            "HEARTBEAT_LEASE_AT_RISK",
            job_id=job_id,
            worker_id=worker_id,
            duration_seconds=0,
            consecutive_failures=0,
            seconds_until_expiry=seconds_until_expiry,
        )
        (request_cancel or cancel_event.set)()


def _heartbeat_loop(
    jobs: JobRepository,
    job_id: str,
    owner: str,
    lease_token: str,
    worker_id: str,
    lease_seconds: float,
    heartbeat_seconds: float,
    initial_lease_expires_at: float,
    database_busy_timeout_seconds: float,
    cancel_event: threading.Event,
    *,
    monotonic_clock: Callable[[], float] = time.monotonic,
    wall_clock: Callable[[], float] = now,
    _start_watchdog: bool = True,
    _publication_gate: _HeartbeatPublicationGate | None = None,
) -> None:
    request_local_cancel = (
        _publication_gate.request_local_cancel
        if _publication_gate is not None
        else cancel_event.set
    )
    wait_for_cancel = (
        _publication_gate.wait
        if _publication_gate is not None
        else cancel_event.wait
    )
    stop_requested = (
        _publication_gate.stop_requested
        if _publication_gate is not None
        else lambda: False
    )
    try:
        lease = _LeaseDeadline(
            initial_lease_expires_at,
            monotonic_clock=monotonic_clock,
            wall_clock=wall_clock,
        )
    except ValueError:
        _heartbeat_diagnostic(
            "HEARTBEAT_FATAL_INTERNAL_ERROR",
            job_id=job_id,
            worker_id=worker_id,
            duration_seconds=0,
            consecutive_failures=0,
            exception_type="InvalidLeaseExpiry",
        )
        request_local_cancel()
        return
    safety_lead = _lease_safety_lead(heartbeat_seconds)
    watchdog: threading.Thread | None = None
    if _start_watchdog:
        watchdog = threading.Thread(
            target=lease.watch,
            args=(cancel_event,),
            kwargs={
                "safety_lead": safety_lead,
                "job_id": job_id,
                "worker_id": worker_id,
                "request_cancel": request_local_cancel,
            },
            daemon=True,
            name=f"lease-watchdog-{job_id}",
        )
        watchdog.start()
    next_wait = heartbeat_seconds
    consecutive_contention = 0
    try:
        while True:
            clock_now = monotonic_clock()
            seconds_until_expiry = lease.current() - clock_now
            latest_safe_wait = seconds_until_expiry - safety_lead
            if latest_safe_wait <= 0:
                _heartbeat_diagnostic(
                    "HEARTBEAT_LEASE_AT_RISK",
                    job_id=job_id,
                    worker_id=worker_id,
                    duration_seconds=0,
                    consecutive_failures=consecutive_contention,
                    seconds_until_expiry=seconds_until_expiry,
                )
                request_local_cancel()
                return
            if wait_for_cancel(min(next_wait, latest_safe_wait)):
                return
            if stop_requested():
                return
            started = monotonic_clock()
            operation_budget = lease.current() - started - safety_lead
            per_lock_busy_timeout = min(
                database_busy_timeout_seconds,
                heartbeat_seconds / 2.0,
                operation_budget / 3.0,
            )
            # SQLite busy_timeout is integer milliseconds. Do not round a tiny
            # budget up and accidentally spend it twice at BEGIN and COMMIT.
            if per_lock_busy_timeout < 0.001:
                _heartbeat_diagnostic(
                    "HEARTBEAT_LEASE_AT_RISK",
                    job_id=job_id,
                    worker_id=worker_id,
                    duration_seconds=0,
                    consecutive_failures=consecutive_contention,
                    seconds_until_expiry=lease.current() - started,
                )
                request_local_cancel()
                return
            try:
                renewed_until = jobs.heartbeat(
                    job_id,
                    owner,
                    lease_token,
                    worker_id,
                    lease_seconds,
                    per_lock_busy_timeout,
                )
            except sqlite3.OperationalError as error:
                completed = monotonic_clock()
                elapsed = completed - started
                if not _transient_sqlite_contention(error):
                    _heartbeat_diagnostic(
                        "HEARTBEAT_FATAL_DATABASE_ERROR",
                        job_id=job_id,
                        worker_id=worker_id,
                        duration_seconds=elapsed,
                        consecutive_failures=consecutive_contention + 1,
                        exception_type=type(error).__name__,
                    )
                    request_local_cancel()
                    return
                consecutive_contention += 1
                seconds_until_expiry = lease.current() - completed
                _heartbeat_diagnostic(
                    "HEARTBEAT_DATABASE_CONTENTION",
                    job_id=job_id,
                    worker_id=worker_id,
                    duration_seconds=elapsed,
                    consecutive_failures=consecutive_contention,
                    seconds_until_expiry=seconds_until_expiry,
                )
                retry_window = seconds_until_expiry - safety_lead
                if retry_window < 0.003:
                    _heartbeat_diagnostic(
                        "HEARTBEAT_LEASE_AT_RISK",
                        job_id=job_id,
                        worker_id=worker_id,
                        duration_seconds=elapsed,
                        consecutive_failures=consecutive_contention,
                        seconds_until_expiry=seconds_until_expiry,
                    )
                    request_local_cancel()
                    return
                backoff = min(
                    heartbeat_seconds,
                    0.05 * (2 ** min(consecutive_contention - 1, 6)),
                )
                next_wait = min(backoff, retry_window - 0.003)
                continue
            except Exception as error:
                _heartbeat_diagnostic(
                    "HEARTBEAT_FATAL_INTERNAL_ERROR",
                    job_id=job_id,
                    worker_id=worker_id,
                    duration_seconds=monotonic_clock() - started,
                    consecutive_failures=consecutive_contention + 1,
                    exception_type=type(error).__name__,
                )
                request_local_cancel()
                return

            completed = monotonic_clock()
            elapsed = completed - started
            if renewed_until is None:
                _heartbeat_diagnostic(
                    "HEARTBEAT_LEASE_LOST_OR_CANCELLED",
                    job_id=job_id,
                    worker_id=worker_id,
                    duration_seconds=elapsed,
                    consecutive_failures=consecutive_contention,
                )
                request_local_cancel()
                return
            # Validate the renewal against the previously observed monotonic
            # lease horizon before honoring a publication stop. A heartbeat
            # that committed after expiry cannot become safe merely because
            # publication requested quiescence while SQLite was in flight.
            if not lease.renew(renewed_until, observed_at=completed):
                _heartbeat_diagnostic(
                    "HEARTBEAT_LEASE_AT_RISK",
                    job_id=job_id,
                    worker_id=worker_id,
                    duration_seconds=elapsed,
                    consecutive_failures=consecutive_contention,
                    seconds_until_expiry=lease.current() - completed,
                )
                request_local_cancel()
                return
            if stop_requested():
                return
            if cancel_event.is_set():
                return
            if consecutive_contention:
                _heartbeat_diagnostic(
                    "HEARTBEAT_RECOVERED",
                    job_id=job_id,
                    worker_id=worker_id,
                    duration_seconds=elapsed,
                    consecutive_failures=consecutive_contention,
                )
            elif elapsed >= heartbeat_seconds:
                _heartbeat_diagnostic(
                    "HEARTBEAT_SLOW",
                    job_id=job_id,
                    worker_id=worker_id,
                    duration_seconds=elapsed,
                    consecutive_failures=0,
                )
            consecutive_contention = 0
            next_wait = heartbeat_seconds
    finally:
        lease.stop()
        if watchdog is not None:
            watchdog.join()


def _transient_sqlite_contention(error: sqlite3.OperationalError) -> bool:
    code = getattr(error, "sqlite_errorcode", None)
    if isinstance(code, int) and (code & 0xFF) in {
        sqlite3.SQLITE_BUSY,
        sqlite3.SQLITE_LOCKED,
    }:
        return True
    normalized = str(error).lower()
    return "database is locked" in normalized or "database table is locked" in normalized


def _heartbeat_diagnostic(
    event: str,
    *,
    job_id: str,
    worker_id: str,
    duration_seconds: float,
    consecutive_failures: int,
    seconds_until_expiry: float | None = None,
    exception_type: str | None = None,
) -> None:
    record: dict[str, object] = {
        "component": "worker-heartbeat",
        "event": event,
        "job_id": job_id,
        "worker_id": worker_id,
        "duration_ms": round(max(0.0, duration_seconds) * 1000, 3),
        "consecutive_failures": consecutive_failures,
    }
    if seconds_until_expiry is not None:
        record["seconds_until_expiry"] = round(seconds_until_expiry, 3)
    if exception_type is not None:
        record["exception_type"] = exception_type
    print(canonical_json(record), file=sys.stderr, flush=True)


def _finish_worker(db: Database, worker_id: str, state: str, error: str | None) -> None:
    with db.transaction(immediate=True) as connection:
        timestamp = now()
        connection.execute(
            """
            UPDATE workers SET state=?,last_activity=?,current_job=NULL,error=?
            WHERE worker_id=? AND state IN ('STARTING','RUNNING')
              AND NOT EXISTS (
                SELECT 1 FROM jobs j
                WHERE j.job_id=workers.current_job
                  AND j.state IN ('CLAIMED','RUNNING')
                  AND (j.lease_expires_at IS NULL OR j.lease_expires_at < ?)
              )
            """,
            (
                state,
                timestamp,
                redact(error) if error else None,
                worker_id,
                timestamp,
            ),
        )


def _validation_labels(validations: list[ValidationResult]) -> list[str]:
    """Aggregate only explicit claims made by passing external validators."""

    labels = {"GENERATED"}
    for validation in validations:
        if validation.passed:
            labels.update(validation.claims)
    order = [
        "GENERATED", "BUILDS", "TESTED", "FUZZED", "BENCHMARKED",
        "REVIEWED", "TRANSFER_VERIFIED", "PRODUCTIONIZED", "PARTIAL",
    ]
    return [label for label in order if label in labels]


def _enforce_validator_execution_policy(
    specifications: object, *, allow_host_commands: bool
) -> None:
    """Fence the validators the handler actually returned, before execution.

    Scheduler payload inspection is only an optimization: deterministic handlers
    can synthesize validators that were absent from the job payload.  The worker
    therefore classifies the final ``HandlerResult`` immediately before
    ``Validator.run`` and blocks every executable form while the host-command
    escape hatch is disabled.
    """

    if not isinstance(specifications, list):
        raise HandlerFailure(
            "handler returned a malformed validator envelope",
            kind="blocked_validator_execution_policy",
            retryable=False,
        )
    for index, specification in enumerate(specifications, start=1):
        if not isinstance(specification, dict):
            raise HandlerFailure(
                f"handler validator {index} is not an object",
                kind="blocked_validator_execution_policy",
                retryable=False,
            )
        kind = specification.get("type")
        if not isinstance(kind, str) or not kind:
            raise HandlerFailure(
                f"handler validator {index} has a malformed type",
                kind="blocked_validator_execution_policy",
                retryable=False,
            )
        executable = kind == "command"
        if kind == "review_acceptance":
            mode = specification.get("mode", "closed")
            if not isinstance(mode, str) or mode not in {"closed", "command"}:
                raise HandlerFailure(
                    f"handler validator {index} has a malformed review mode",
                    kind="blocked_validator_execution_policy",
                    retryable=False,
                )
            executable = mode == "command"
        if executable and not allow_host_commands:
            raise HandlerFailure(
                "host command validators are disabled by factory policy",
                kind="blocked_validator_execution_policy",
                retryable=False,
            )


def _validated_byox_cutover_contract(
    validators: list[dict[str, object]],
    archive_paths: tuple[str, ...] | None,
    metadata: dict[str, object],
) -> tuple[str, str] | None:
    """Return exact validation/archive hashes for an authoritative cutover.

    Structural BYOX validation and the Codex backend capability gate are
    authoritative only after the handler replaces the worker-visible tree with
    a fresh-inode snapshot. Validate that controller record before running the
    gate, then compare both the post-validation workspace and projected archive
    against these hashes.
    """

    requires_cutover = any(
        isinstance(specification, dict)
        and specification.get("type") == "byox_code_presence"
        for specification in validators
    )
    has_executable_validator = any(
        isinstance(specification, dict)
        and (
            specification.get("type") == "command"
            or (
                specification.get("type") == "review_acceptance"
                and specification.get("mode") == "command"
            )
        )
        for specification in validators
    )
    byox_raw = metadata.get("byox_validation_cutover")
    generic_raw = metadata.get("authoritative_validation_cutover")
    if byox_raw is not None and generic_raw is not None:
        raise HandlerFailure(
            "multiple authoritative cutover records are not allowed",
            kind="unsafe_validator_contract",
            retryable=False,
        )
    if not requires_cutover:
        if byox_raw is not None:
            raise HandlerFailure(
                "BYOX cutover metadata exists without the structural gate",
                kind="unsafe_validator_contract",
                retryable=False,
            )
        raw = generic_raw
        if raw is None:
            return None
    else:
        if generic_raw is not None:
            raise HandlerFailure(
                "BYOX structural gate has the wrong cutover record type",
                kind="unsafe_validator_contract",
                retryable=False,
            )
        raw = byox_raw
    if has_executable_validator:
        raise HandlerFailure(
            "authoritative cutovers cannot be mixed with executable validators",
            kind="unsafe_validator_contract",
            retryable=False,
        )
    if not isinstance(raw, dict):
        raise HandlerFailure(
            "authoritative validation lacks a cutover record",
            kind="unsafe_validator_contract",
            retryable=False,
        )
    manifest = raw.get("manifest_sha256")
    body = {key: value for key, value in raw.items() if key != "manifest_sha256"}
    expected_manifest = hashlib.sha256(
        canonical_json(body).encode("utf-8")
    ).hexdigest()
    validation_checksum = raw.get("validation_snapshot_checksum")
    selected_checksum = raw.get("selected_output_checksum")
    raw_paths = raw.get("archive_paths")
    expected_paths: tuple[str, ...] | None
    if raw_paths is None:
        expected_paths = None
    elif isinstance(raw_paths, list) and all(
        isinstance(path, str) for path in raw_paths
    ):
        expected_paths = tuple(raw_paths)
    else:
        expected_paths = ()
    def valid_digest(value: object) -> bool:
        return bool(
            isinstance(value, str)
            and re.fullmatch(r"[0-9a-f]{64}", value) is not None
        )
    if (
        raw.get("schema_version") != 1
        or raw.get("classification")
        != "factory-authoritative-validation-snapshot"
        or raw.get("validation_snapshot_checksum_algorithm")
        != "tree-sha256-v2"
        or raw.get("selected_output_checksum_algorithm") != "tree-sha256-v2"
        or not valid_digest(manifest)
        or manifest != expected_manifest
        or not valid_digest(validation_checksum)
        or not valid_digest(selected_checksum)
        or expected_paths != archive_paths
    ):
        raise HandlerFailure(
            "authoritative cutover contract is malformed or inconsistent",
            kind="unsafe_validator_contract",
            retryable=False,
        )
    assert isinstance(validation_checksum, str)
    assert isinstance(selected_checksum, str)
    return validation_checksum, selected_checksum


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Internal Learning Factory worker")
    parser.add_argument("--job", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--lease-token", required=True)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    return run_worker(args.job, args.owner, args.lease_token, args.config)


if __name__ == "__main__":
    raise SystemExit(main())
