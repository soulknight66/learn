from __future__ import annotations

import argparse
import os
import signal
import socket
import threading
import traceback
from pathlib import Path

from .config import load_settings
from .db import Database
from .handlers import HandlerFailure, JobHandlers
from .jobs import ClaimedJob, JobError, JobRepository
from .run_provenance import (
    capture_run_provenance,
    unavailable_run_provenance,
    write_run_provenance,
)
from .util import canonical_json, new_id, now, redact, repository_revision, tree_sha256
from .validation import ValidationResult, Validator
from .workspace import PreparedArtifact, WorkspaceError, WorkspaceManager


def run_worker(job_id: str, owner: str, lease_token: str, config_path: Path | None = None) -> int:
    settings = load_settings(config_path)
    db = Database(settings.database, settings.migrations)
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
    effective_model = job.model or settings.backend.model
    effective_reasoning = job.reasoning_effort or settings.backend.reasoning_effort
    cancel_event = threading.Event()
    supervisor_stop_event = threading.Event()

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
        supervisor_stop_event.set()
        cancel_event.set()

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
        jobs.start(job_id, owner, lease_token, worker_id, str(workspace))
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
        args=(jobs, job_id, owner, lease_token, worker_id, settings.lease_seconds, settings.heartbeat_seconds, cancel_event),
        daemon=True,
        name=f"heartbeat-{job_id}",
    )
    heartbeat.start()
    exit_code = 1
    prepared: PreparedArtifact | None = None
    archive_projection: Path | None = None
    try:
        result = JobHandlers(settings, db, manager).execute(job, workspace, log_dir, cancel_event)
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
            jobs.interrupt(
                job_id, owner, lease_token, worker_id,
                reason="worker stopped by controller during handler execution",
            )
            exit_code = 143
        else:
            validations = Validator(db).run(
                job_id,
                workspace,
                result.validators,
                log_dir,
                attempt_number=job.attempt_count,
                cancel_event=cancel_event,
            )
            if jobs.cancellation_requested(job_id):
                jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
                exit_code = 130
            elif supervisor_stop_event.is_set():
                jobs.interrupt(
                    job_id, owner, lease_token, worker_id,
                    reason="worker stopped by controller during validation",
                )
                exit_code = 143
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
                    jobs.interrupt(
                        job_id,
                        owner,
                        lease_token,
                        worker_id,
                        reason="worker stopped by controller during artifact preparation",
                    )
                    exit_code = 143
                else:
                    jobs.succeed_with_artifact(
                        job_id,
                        owner,
                        lease_token,
                        worker_id,
                        prepared,
                        on_publish=result.on_publish,
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
    except HandlerFailure as error:
        if jobs.cancellation_requested(job_id):
            jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
            exit_code = 130
        elif supervisor_stop_event.is_set():
            jobs.interrupt(
                job_id, owner, lease_token, worker_id,
                reason=f"worker stopped by controller: {error}",
            )
            exit_code = 143
        elif error.kind == "cancelled" or cancel_event.is_set():
            jobs.fail(
                job_id,
                owner,
                lease_token,
                worker_id,
                kind="worker_interrupted",
                error=str(error),
                retryable=True,
            )
            exit_code = 6
        elif error.kind.startswith("blocked_"):
            jobs.block(
                job_id, owner, lease_token, worker_id, kind=error.kind, error=str(error)
            )
            exit_code = 8
        else:
            jobs.fail(
                job_id, owner, lease_token, worker_id, kind=error.kind, error=str(error), retryable=error.retryable
            )
            exit_code = 6
    except Exception as error:
        detail = f"{type(error).__name__}: {error}\n{traceback.format_exc()}"
        try:
            if jobs.cancellation_requested(job_id):
                jobs.finish_cancelled(job_id, owner, lease_token, worker_id)
                exit_code = 130
            elif supervisor_stop_event.is_set():
                jobs.interrupt(
                    job_id, owner, lease_token, worker_id,
                    reason="worker stopped by controller after internal error",
                )
                exit_code = 143
            else:
                jobs.fail(
                    job_id, owner, lease_token, worker_id,
                    kind="worker_crash", error=detail, retryable=True,
                )
        except JobError:
            pass
        if exit_code not in (130, 143):
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
        cancel_event.set()
        heartbeat.join(timeout=settings.heartbeat_seconds + 1)
        state = "SUCCEEDED" if exit_code == 0 else "CANCELLED" if exit_code == 130 else "INTERRUPTED" if exit_code == 143 else "FAILED"
        _finish_worker(db, worker_id, state, None if exit_code == 0 else f"exit {exit_code}")
        with db.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE job_runs SET finished_at=?,exit_code=? WHERE run_id=?",
                (now(), exit_code, run_id),
            )
    return exit_code


def _heartbeat_loop(
    jobs: JobRepository,
    job_id: str,
    owner: str,
    lease_token: str,
    worker_id: str,
    lease_seconds: float,
    heartbeat_seconds: float,
    cancel_event: threading.Event,
) -> None:
    while not cancel_event.wait(heartbeat_seconds):
        try:
            if jobs.cancellation_requested(job_id):
                cancel_event.set()
                return
            if not jobs.heartbeat(job_id, owner, lease_token, worker_id, lease_seconds):
                cancel_event.set()
                return
        except Exception:
            # A single transient SQLite contention does not surrender an otherwise valid lease.
            continue


def _finish_worker(db: Database, worker_id: str, state: str, error: str | None) -> None:
    with db.transaction(immediate=True) as connection:
        connection.execute(
            """
            UPDATE workers SET state=?,last_activity=?,current_job=NULL,error=?
            WHERE worker_id=? AND state IN ('STARTING','RUNNING')
            """,
            (state, now(), redact(error) if error else None, worker_id),
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
