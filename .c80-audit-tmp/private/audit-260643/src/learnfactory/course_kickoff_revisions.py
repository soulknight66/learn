from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from .backend_policy import MASS_SEED_EXECUTION_POLICY, with_mass_seed_backend_policy
from .course_submission import student_submission_binding_payload
from .db import Database
from .jobs import JobRepository
from .learners import unambiguous_examiner_evaluation_result
from .util import canonical_json, now, slugify


KICKOFF_REVISION_POLICY_KIND = "csdiy_course_kickoff_revision"
KICKOFF_REVISION_POLICY_VERSION = 2
_REVISION_ROLES = {"student_revision", "examiner_revision"}
_NONPASSING_RESULTS = {"REVISE", "FAIL"}


def _kickoff_payloads_equivalent(
    persisted: dict[str, Any], expected: dict[str, Any]
) -> bool:
    """Accept only the exact pre-execution_policy kickoff revision shape."""

    if persisted == expected:
        return True
    legacy = dict(expected)
    if legacy.get("execution_policy") != MASS_SEED_EXECUTION_POLICY:
        return False
    legacy.pop("execution_policy")
    return persisted == legacy


def _decoded(raw: object, expected: type, default: Any) -> Any:
    try:
        value = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return default
    return value if isinstance(value, expected) else default


def _verified_artifact(
    db: Database, job_id: str, expected_type: str
) -> dict[str, Any] | None:
    with db.connect() as connection:
        row = connection.execute(
            """
            SELECT a.artifact_id,a.type,a.checksum,a.attempt_number,
                   a.checksum_algorithm,a.integrity_status
            FROM jobs j JOIN artifacts a
              ON a.job_id=j.job_id AND a.attempt_number=j.attempt_count
            WHERE j.job_id=? AND j.state='SUCCEEDED' AND a.type=?
              AND a.checksum_algorithm='tree-sha256-v2'
              AND a.integrity_status='VERIFIED_V2'
            ORDER BY a.created_at DESC,a.artifact_id DESC
            LIMIT 1
            """,
            (job_id, expected_type),
        ).fetchone()
    return dict(row) if row is not None else None


def _evaluation_result(db: Database, job_id: str) -> str | None:
    """Read one unambiguous attempt-bound result from the examiner hook."""
    with db.connect() as connection:
        return unambiguous_examiner_evaluation_result(connection, job_id)


def _artifact_binding(job_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "artifact_id": artifact["artifact_id"],
        "artifact_type": artifact["type"],
        "artifact_checksum": artifact["checksum"],
        "artifact_checksum_algorithm": artifact["checksum_algorithm"],
        "artifact_attempt": artifact["attempt_number"],
    }


def _revision_identity(snapshot_without_identity: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        canonical_json(snapshot_without_identity).encode("utf-8")
    ).hexdigest()
    return f"csdiy-kickoff-revision-v{KICKOFF_REVISION_POLICY_VERSION}-{digest[:24]}"


def _revision_job_ids(revision_id: str) -> dict[str, str]:
    digest = revision_id.rsplit("-", 1)[-1]
    prefix = (
        f"job_csdiy_kickoff_rev_v{KICKOFF_REVISION_POLICY_VERSION}_{digest}"
    )
    return {
        "student_revision": f"{prefix}_student_target",
        "examiner_revision": f"{prefix}_examiner",
    }


def _new_revision_snapshot(
    course_snapshot: dict[str, Any],
    *,
    attempt_number: int,
    preparation_job_id: str,
    preparation_artifact: dict[str, Any],
    prior_student_job_id: str,
    prior_student_artifact: dict[str, Any],
    prior_examiner_job_id: str,
    prior_examiner_artifact: dict[str, Any],
    prior_evaluation_result: str,
) -> dict[str, Any]:
    course = course_snapshot["course"]
    source = course_snapshot["source"]
    catalog_snapshot_sha256 = hashlib.sha256(
        canonical_json(course_snapshot).encode("utf-8")
    ).hexdigest()
    base = {
        "schema_version": 1,
        "policy_version": KICKOFF_REVISION_POLICY_VERSION,
        "attempt_number": attempt_number,
        "student_id": "student-target",
        "course": {
            "course_id": course["course_id"],
            "catalog_snapshot_sha256": catalog_snapshot_sha256,
        },
        "source": {
            "source_id": source["source_id"],
            "commit_hash": source["commit_hash"],
        },
        "preparation": _artifact_binding(
            preparation_job_id, preparation_artifact
        ),
        "prior_student": _artifact_binding(
            prior_student_job_id, prior_student_artifact
        ),
        "prior_examiner": {
            **_artifact_binding(prior_examiner_job_id, prior_examiner_artifact),
            "evaluation_result": prior_evaluation_result,
        },
        "completion_scope": {
            "kickoff_attempt": attempt_number,
            "course_completion": "NOT_CLAIMED",
            "transfer_verification": "NOT_CLAIMED",
        },
    }
    revision_id = _revision_identity(base)
    snapshot = {**base, "revision_id": revision_id}
    snapshot["revision_snapshot_sha256"] = hashlib.sha256(
        canonical_json(snapshot).encode("utf-8")
    ).hexdigest()
    return snapshot


def _revision_snapshot_error(
    snapshot: dict[str, Any],
    *,
    course_snapshot: dict[str, Any],
    expected: dict[str, Any],
) -> str | None:
    if snapshot != expected:
        return "kickoff revision snapshot conflicts with current immutable evidence"
    checksum = snapshot.get("revision_snapshot_sha256")
    if not isinstance(checksum, str) or len(checksum) != 64:
        return "kickoff revision snapshot checksum is missing"
    without_checksum = dict(snapshot)
    without_checksum.pop("revision_snapshot_sha256", None)
    if hashlib.sha256(
        canonical_json(without_checksum).encode("utf-8")
    ).hexdigest() != checksum:
        return "kickoff revision snapshot checksum mismatch"
    identity_input = dict(without_checksum)
    revision_id = identity_input.pop("revision_id", None)
    if revision_id != _revision_identity(identity_input):
        return "kickoff revision ID is not derived from its snapshot"
    course = snapshot.get("course")
    source = snapshot.get("source")
    if (
        not isinstance(course, dict)
        or course.get("course_id") != course_snapshot["course"]["course_id"]
        or not isinstance(source, dict)
        or source.get("source_id") != course_snapshot["source"]["source_id"]
        or source.get("commit_hash") != course_snapshot["source"]["commit_hash"]
    ):
        return "kickoff revision source or course scope mismatch"
    return None


def _evaluation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "result": {"type": "string", "enum": ["PASS", "REVISE", "FAIL"]},
            "score": {"type": "number", "minimum": 0, "maximum": 100},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "transfer_gaps": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["result", "score", "evidence", "transfer_gaps"],
        "additionalProperties": False,
    }


def _bound_input(
    binding: dict[str, Any], subpath: str, destination: str
) -> dict[str, Any]:
    return {
        "job_id": binding["job_id"],
        "subpath": subpath,
        "destination": destination,
        "artifact_type": binding["artifact_type"],
        "artifact_id": binding["artifact_id"],
        "artifact_checksum": binding["artifact_checksum"],
        "artifact_attempt": binding["artifact_attempt"],
        "checksum_algorithm": binding["artifact_checksum_algorithm"],
    }


def _revision_graph_specs(
    course_snapshot: dict[str, Any],
    revision_snapshot: dict[str, Any],
    *,
    gate_job_id: str,
) -> dict[str, dict[str, Any]]:
    course = course_snapshot["course"]
    course_id = str(course["course_id"])
    attempt_number = int(revision_snapshot["attempt_number"])
    revision_id = str(revision_snapshot["revision_id"])
    ids = _revision_job_ids(revision_id)
    preparation = revision_snapshot["preparation"]
    prior_student = revision_snapshot["prior_student"]
    prior_examiner = revision_snapshot["prior_examiner"]
    safe_slug = slugify(str(course.get("slug") or course.get("title") or course_id))[
        :80
    ]
    semantic = (
        f"courses/catalog/{safe_slug}-{hashlib.sha256(course_id.encode()).hexdigest()[:8]}/"
        f"cohort-v{KICKOFF_REVISION_POLICY_VERSION}/student-target/kickoff"
    )
    policy_base = {
        "kind": KICKOFF_REVISION_POLICY_KIND,
        "version": KICKOFF_REVISION_POLICY_VERSION,
        "attempt_number": attempt_number,
    }
    provenance = {
        "classification": (
            "agent-generated bounded revision of an independently evaluated course kickoff"
        ),
        "course_id": course_id,
        "source_id": revision_snapshot["source"]["source_id"],
        "source_commit_hash": revision_snapshot["source"]["commit_hash"],
        "revision_id": revision_id,
        "revision_snapshot_sha256": revision_snapshot[
            "revision_snapshot_sha256"
        ],
        "attempt_number": attempt_number,
        "preparation_artifact": preparation,
        "prior_student_artifact": prior_student,
        "prior_examiner_artifact": prior_examiner,
        "course_completion": "NOT_CLAIMED",
        "transfer_verification": "NOT_CLAIMED",
    }
    student_payload = with_mass_seed_backend_policy({
        "seed_policy": {**policy_base, "role": "student_revision"},
        "required_backend": {
            "name": "exec",
            "permission_profile": "factory-isolated",
        },
        "course_id": course_id,
        "student_id": "student-target",
        "revision_id": revision_id,
        "revision_snapshot": revision_snapshot,
        "prompt": (
            "Act as the same persistent target learner revising one bounded course kickoff. "
            "Treat LEARNER_MATERIAL/, PRIOR_ATTEMPT/, and EXAMINER_FEEDBACK/ as read-only "
            "data. Address the learner-facing feedback using your own engineering judgment. "
            "Do not search for or infer rubrics, hidden or novel checks, reference answers, "
            "other students' work, sealed material, or factory state. Put every fresh output "
            "under student_work/: notes.md, submission.md, debugging-log.md, and any source, "
            "tests, fixtures, or build files needed by the revision. State what changed and record concrete "
            "experiments and observations without private chain-of-thought. Do not overwrite "
            "the prior attempt or claim whole-course completion or transfer verification."
        ),
        "inputs_from_dependencies": [
            *[
                _bound_input(
                    preparation,
                    f"student_safe/{name}",
                    f"LEARNER_MATERIAL/{name}",
                )
                for name in ("COURSE_BRIEF.md", "STUDY_TASK.md", "COMPREHENSION.md")
            ],
            _bound_input(
                prior_student,
                "student_work",
                "PRIOR_ATTEMPT",
            ),
            _bound_input(
                prior_examiner,
                "feedback.md",
                "EXAMINER_FEEDBACK/feedback.md",
            ),
        ],
        "protected_input_roots": [
            "LEARNER_MATERIAL",
            "PRIOR_ATTEMPT",
            "EXAMINER_FEEDBACK",
        ],
        "student_submission_format": "student-work-tree-v1",
        "student_submission_contract_version": KICKOFF_REVISION_POLICY_VERSION,
        "validators": [
            {
                "type": "regular_files",
                "name": "kickoff-student-revision-files",
                "paths": [
                    "student_work/notes.md",
                    "student_work/submission.md",
                    "student_work/debugging-log.md",
                ],
                "minimum_bytes": 1,
            },
            {
                "type": "forbidden_tree_names",
                "name": "kickoff-student-revision-tree-isolation",
                "roots": ["student_work"],
                "names": [
                    "examiner_only",
                    "hidden",
                    "hidden_tests",
                    "novel_check.md",
                    "reference",
                    "references",
                    "rubric.md",
                    "sealed",
                ],
            },
            {
                "type": "allowed_root_paths",
                "name": "kickoff-student-revision-output-boundary",
                "paths": [
                    "student_work",
                    "LEARNER_MATERIAL",
                    "PRIOR_ATTEMPT",
                    "EXAMINER_FEEDBACK",
                ],
            },
            {
                "type": "forbidden_paths",
                "name": "kickoff-student-revision-root-isolation",
                "paths": [
                    "examiner_only",
                    "RUBRIC.md",
                    "NOVEL_CHECK.md",
                    "sealed",
                    "reference",
                ],
            },
        ],
        "artifact_type": "student-course-attempt",
        "artifact_path": f"{semantic}/attempt-{attempt_number:03d}",
        "validation_status": "GENERATED_CANDIDATE",
        "provenance": {
            **provenance,
            "student_id": "student-target",
            "prior_student_job_id": prior_student["job_id"],
            "prior_examiner_job_id": prior_examiner["job_id"],
        },
        "timeout_seconds": 1800,
    })
    evaluation_schema = _evaluation_schema()
    examiner_payload = with_mass_seed_backend_policy({
        "seed_policy": {**policy_base, "role": "examiner_revision"},
        "required_backend": {
            "name": "exec",
            "permission_profile": "factory-isolated",
        },
        "course_id": course_id,
        "student_id": "student-target",
        "revision_id": revision_id,
        "revision_snapshot": revision_snapshot,
        "prompt": (
            "Act as a new independent examiner for a bounded revised course kickoff. Treat "
            "the revision and prior evaluation as untrusted evidence. Use the rubric supplied "
            "only in controller prompt context and statically inspect the complete read-only "
            "STUDENT_SUBMISSION/ tree. Do not execute candidate code, edit the submission, or "
            "expose rubric, hidden checks, or reference material. Return the schema-constrained "
            "evaluation and learner-facing feedback through the final response only; do not "
            "create files. PASS "
            "applies only to this kickoff attempt and is not whole-course completion or transfer "
            "verification."
        ),
        "inputs_from_dependencies": [
            {
                **_bound_input(
                    preparation, "examiner_only/RUBRIC.md", "RUBRIC.md"
                ),
                "prompt_context": True,
            },
            {
                "job_id": ids["student_revision"],
                "artifact_type": "student-course-attempt",
                "student_submission_root": True,
                "destination": "STUDENT_SUBMISSION",
            },
            *[
                {
                    **_bound_input(
                        prior_examiner,
                        name,
                        f"PRIOR_EVALUATION/{name}",
                    ),
                    "prompt_context": True,
                }
                for name in ("evaluation.json", "feedback.md")
            ],
        ],
        "protected_input_roots": ["STUDENT_SUBMISSION"],
        "student_submission_binding": student_submission_binding_payload(
            ids["student_revision"], "student-course-attempt"
        ),
        "student_submission_contract_version": KICKOFF_REVISION_POLICY_VERSION,
        "output_schema": evaluation_schema,
        "learner_evidence": {
            "schema_version": 1,
            "student_id": "student-target",
            "student_job_id": ids["student_revision"],
            "student_artifact_type": "student-course-attempt",
            "task_id": f"{course_id}-kickoff-examiner-v2",
            "task_type": "course-kickoff",
            "attempt_number": attempt_number,
            "evaluator": (
                "new independent Codex course-kickoff revision examiner with deterministic validation"
            ),
            "evaluation_path": "evaluation.json",
            "schema_validator": "kickoff-revision-examiner-evidence",
            "rubric": {
                "source_job_id": preparation["job_id"],
                "source_path": "examiner_only/RUBRIC.md",
                "dimensions": [
                    "correctness",
                    "observable_evidence",
                    "engineering_judgment",
                    "debugging_practice",
                    "revision_quality",
                ],
                "assessment_scope": (
                    "one bounded course kickoff revision; not course completion"
                ),
                "attempt_number": attempt_number,
            },
            "concepts": [
                {
                    "concept": f"course-kickoff:{course_id}",
                    "description": (
                        f"Revision evidence from the bounded kickoff for {course.get('title', course_id)}"
                    ),
                    "kind": "independent-course-kickoff-revision-examiner",
                    "source_reference": course_id,
                    "result_weights": {
                        "PASS": 0.3,
                        "REVISE": 0.05,
                        "FAIL": -0.25,
                    },
                }
            ],
        },
        "validators": [
            {
                "type": "regular_files",
                "name": "kickoff-revision-examiner-files",
                "paths": ["evaluation.json", "feedback.md"],
                "minimum_bytes": 1,
            },
            {
                "type": "json_schema",
                "name": "kickoff-revision-examiner-evidence",
                "path": "evaluation.json",
                "schema": evaluation_schema,
            },
        ],
        "artifact_type": "independent-course-evaluation",
        "artifact_path": f"{semantic}/evaluation-{attempt_number:03d}",
        "validation_status": "GENERATED_CANDIDATE",
        "provenance": {
            **provenance,
            "student_job_id": ids["student_revision"],
            "prior_examiner_job_id": prior_examiner["job_id"],
            "evaluator_independence": "new separate Codex process and workspace",
        },
        "timeout_seconds": 1200,
    })
    return {
        "student_revision": {
            "job_id": ids["student_revision"],
            "worker_type": "student",
            "payload": student_payload,
            "dependencies": [
                gate_job_id,
                preparation["job_id"],
                prior_student["job_id"],
                prior_examiner["job_id"],
            ],
        },
        "examiner_revision": {
            "job_id": ids["examiner_revision"],
            "worker_type": "examiner",
            "payload": examiner_payload,
            "dependencies": [
                gate_job_id,
                preparation["job_id"],
                ids["student_revision"],
                prior_examiner["job_id"],
            ],
        },
    }


def _revision_groups(
    db: Database,
    course_id: str,
    *,
    source_id: str,
    source_commit_hash: str,
) -> dict[int, dict[str, Any]]:
    groups: dict[int, dict[str, Any]] = {}
    with db.connect() as connection:
        rows = connection.execute(
            "SELECT job_id,payload_json FROM jobs ORDER BY created_at,job_id"
        ).fetchall()
    for row in rows:
        payload = _decoded(row["payload_json"], dict, {})
        policy = payload.get("seed_policy")
        if not isinstance(policy, dict) or policy.get("kind") != KICKOFF_REVISION_POLICY_KIND:
            continue
        if payload.get("course_id") != course_id:
            continue
        if policy.get("version") != KICKOFF_REVISION_POLICY_VERSION:
            if policy.get("version") == 1:
                # Retain the narrative-only generation as history. It cannot
                # satisfy the v2 evaluator binding and is not part of this
                # revision chain.
                continue
            raise RuntimeError("unsupported CSDIY kickoff revision policy version")
        revision_snapshot = payload.get("revision_snapshot")
        revision_source = (
            revision_snapshot.get("source")
            if isinstance(revision_snapshot, dict)
            else None
        )
        if (
            isinstance(revision_source, dict)
            and (
                revision_source.get("source_id") != source_id
                or revision_source.get("commit_hash") != source_commit_hash
            )
        ):
            # Immutable revision graphs from older active-source snapshots remain
            # valid history but cannot participate in this source revision.
            continue
        attempt_number = policy.get("attempt_number")
        role = policy.get("role")
        if (
            isinstance(attempt_number, bool)
            or not isinstance(attempt_number, int)
            or attempt_number < 2
            or role not in _REVISION_ROLES
        ):
            raise RuntimeError("invalid CSDIY kickoff revision policy")
        group = groups.setdefault(
            attempt_number,
            {"roles": {}, "revision_snapshot": revision_snapshot},
        )
        if group["revision_snapshot"] != revision_snapshot:
            raise RuntimeError("conflicting CSDIY kickoff revision snapshots")
        if role in group["roles"]:
            raise RuntimeError("duplicate CSDIY kickoff revision role")
        group["roles"][role] = str(row["job_id"])
    return groups


def _supersede_legacy_revision_jobs(
    db: Database, course_snapshot: dict[str, Any]
) -> list[str]:
    """Cancel only idle v1 kickoff revisions; preserve active/terminal history."""

    course_id = str(course_snapshot["course"]["course_id"])
    source_id = str(course_snapshot["source"]["source_id"])
    source_commit = str(course_snapshot["source"]["commit_hash"])
    reason = "superseded by checksum-bound kickoff revision contract v2"

    def legacy_scope(
        row: sqlite3.Row | None,
    ) -> tuple[dict[str, Any], str] | None:
        if (
            row is None
            or row["owner"] is not None
            or row["state"]
            not in {"DISCOVERED", "READY", "RETRY_WAIT", "BLOCKED"}
        ):
            return None
        payload = _decoded(row["payload_json"], dict, {})
        policy = payload.get("seed_policy")
        revision = payload.get("revision_snapshot")
        revision_source = (
            revision.get("source") if isinstance(revision, dict) else None
        )
        attempt_number = (
            policy.get("attempt_number") if isinstance(policy, dict) else None
        )
        role = policy.get("role") if isinstance(policy, dict) else None
        if (
            not isinstance(policy, dict)
            or set(policy) != {"kind", "version", "attempt_number", "role"}
            or policy.get("kind") != KICKOFF_REVISION_POLICY_KIND
            or policy.get("version") != 1
            or isinstance(attempt_number, bool)
            or not isinstance(attempt_number, int)
            or attempt_number < 2
            or role not in _REVISION_ROLES
            or payload.get("course_id") != course_id
            or not isinstance(revision_source, dict)
            or revision_source.get("source_id") != source_id
            or revision_source.get("commit_hash") != source_commit
        ):
            return None
        return payload, str(role)

    candidate_ids: list[str] = []
    with db.connect() as connection:
        rows = connection.execute(
            """
            SELECT job_id,state,attempt_count,owner,payload_json
            FROM jobs
            WHERE state IN ('DISCOVERED','READY','RETRY_WAIT','BLOCKED')
              AND owner IS NULL
            ORDER BY job_id
            """
        ).fetchall()
        candidate_ids = [
            str(row["job_id"]) for row in rows if legacy_scope(row) is not None
        ]
    if not candidate_ids:
        return []

    cancelled: list[str] = []
    with db.transaction(immediate=True) as connection:
        for job_id in candidate_ids:
            row = connection.execute(
                """
                SELECT job_id,state,attempt_count,owner,payload_json
                FROM jobs WHERE job_id=?
                """,
                (job_id,),
            ).fetchone()
            scope = legacy_scope(row)
            if scope is None:
                continue
            _, role = scope
            timestamp = now()
            changed = connection.execute(
                """
                UPDATE jobs
                SET state='CANCELLED',cancel_requested=1,retry_at=NULL,
                    owner=NULL,lease_token=NULL,lease_expires_at=NULL,
                    heartbeat_at=NULL,finished_at=?,error=?,
                    failure_kind='superseded_submission_contract'
                WHERE job_id=? AND state=? AND owner IS NULL AND attempt_count=?
                """,
                (
                    timestamp,
                    reason,
                    row["job_id"],
                    row["state"],
                    row["attempt_count"],
                ),
            )
            if changed.rowcount != 1:
                continue
            db.emit_event(
                "controller",
                "JOB_SUPERSEDED",
                job_id=str(row["job_id"]),
                payload={
                    "kind": KICKOFF_REVISION_POLICY_KIND,
                    "course_id": course_id,
                    "role": role,
                    "previous_state": row["state"],
                    "attempt_count": row["attempt_count"],
                    "reason": reason,
                    "superseding_policy_version": KICKOFF_REVISION_POLICY_VERSION,
                    "terminal_history_preserved": True,
                    "active_jobs_untouched": True,
                },
                connection=connection,
            )
            cancelled.append(str(row["job_id"]))
    return cancelled


def _ensure_revision_graph(
    jobs: JobRepository,
    course_snapshot: dict[str, Any],
    revision_snapshot: dict[str, Any],
    *,
    gate_job_id: str,
    score_components: dict[str, float],
    base_priority: float,
) -> tuple[dict[str, str], int]:
    specs = _revision_graph_specs(
        course_snapshot, revision_snapshot, gate_job_id=gate_job_id
    )
    priorities = {
        "student_revision": base_priority,
        "examiner_revision": base_priority - 1,
    }
    created = 0
    identifiers: dict[str, str] = {}
    for role in ("student_revision", "examiner_revision"):
        spec = specs[role]
        job_id = str(spec["job_id"])
        if jobs.get(job_id) is None:
            try:
                jobs.create(
                    "codex_task",
                    str(spec["worker_type"]),
                    dict(spec["payload"]),
                    job_id=job_id,
                    priority=round(priorities[role], 4),
                    score_components=score_components,
                    max_attempts=2,
                    dependencies=list(spec["dependencies"]),
                    model="gpt-5.6-sol",
                    reasoning_effort="ultra",
                )
                created += 1
            except sqlite3.IntegrityError:
                if jobs.get(job_id) is None:
                    raise
        persisted = jobs.get(job_id)
        if persisted is None:
            raise RuntimeError(f"failed to persist kickoff revision job: {job_id}")
        expected_policy = {
            "kind": KICKOFF_REVISION_POLICY_KIND,
            "version": KICKOFF_REVISION_POLICY_VERSION,
            "attempt_number": revision_snapshot["attempt_number"],
            "role": role,
        }
        if (
            persisted["type"] != "codex_task"
            or persisted["worker_type"] != spec["worker_type"]
            or persisted["model"] != "gpt-5.6-sol"
            or persisted["reasoning_effort"] != "ultra"
            or persisted["payload"].get("seed_policy") != expected_policy
            or not _kickoff_payloads_equivalent(
                persisted["payload"], spec["payload"]
            )
        ):
            raise RuntimeError(f"CSDIY kickoff revision identity collision: {job_id}")
        with jobs.db.connect() as connection:
            dependencies = {
                str(row["depends_on_job_id"])
                for row in connection.execute(
                    "SELECT depends_on_job_id FROM job_dependencies WHERE job_id=?",
                    (job_id,),
                )
            }
        if dependencies != set(spec["dependencies"]):
            raise RuntimeError(
                f"CSDIY kickoff revision dependency mismatch: {job_id}"
            )
        identifiers[role] = job_id
    return identifiers, created


def _kickoff_scope_id(course_snapshot: dict[str, Any]) -> str:
    scope = {
        "policy_version": KICKOFF_REVISION_POLICY_VERSION,
        "course_id": course_snapshot["course"]["course_id"],
        "source_id": course_snapshot["source"]["source_id"],
        "source_commit_hash": course_snapshot["source"]["commit_hash"],
        "catalog_snapshot_sha256": hashlib.sha256(
            canonical_json(course_snapshot).encode("utf-8")
        ).hexdigest(),
    }
    digest = hashlib.sha256(canonical_json(scope).encode("utf-8")).hexdigest()
    return f"csdiy-kickoff-v{KICKOFF_REVISION_POLICY_VERSION}-{digest[:24]}"


def _record_revision_block(
    db: Database,
    course_snapshot: dict[str, Any],
    *,
    attempt_number: int,
    max_revisions: int,
    evaluation_result: str,
) -> bool:
    reason = (
        "the latest independently evaluated kickoff attempt did not pass and "
        "the configured finite revision limit is exhausted"
    )
    batch_id = _kickoff_scope_id(course_snapshot)
    key = (batch_id, attempt_number, max_revisions)
    expected = (
        str(course_snapshot["course"]["course_id"]),
        str(course_snapshot["source"]["source_id"]),
        str(course_snapshot["source"]["commit_hash"]),
        1,
        evaluation_result,
        reason,
    )
    query = """
        SELECT course_id,source_id,source_commit_hash,sequence,evaluation_result,reason
        FROM course_progression_revision_blocks
        WHERE batch_id=? AND attempt_number=? AND configured_revision_limit=?
    """
    with db.transaction(immediate=True) as connection:
        existing = connection.execute(query, key).fetchone()
        if existing is not None:
            if tuple(existing) != expected:
                raise RuntimeError("CSDIY kickoff revision block conflicts with evidence")
            return False
        inserted = connection.execute(
            """
            INSERT OR IGNORE INTO course_progression_revision_blocks(
                course_id,source_id,source_commit_hash,sequence,batch_id,
                attempt_number,configured_revision_limit,evaluation_result,
                reason,created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                *expected[:4],
                batch_id,
                attempt_number,
                max_revisions,
                evaluation_result,
                reason,
                now(),
            ),
        ).rowcount
        if not inserted:
            existing = connection.execute(query, key).fetchone()
            if existing is None or tuple(existing) != expected:
                raise RuntimeError("CSDIY kickoff revision block conflicts with evidence")
            return False
        db.emit_event(
            "controller",
            "COURSE_KICKOFF_REVISION_BLOCKED",
            payload={
                "course_id": course_snapshot["course"]["course_id"],
                "source_id": course_snapshot["source"]["source_id"],
                "source_commit_hash": course_snapshot["source"]["commit_hash"],
                "kickoff_scope_id": batch_id,
                "attempt_number": attempt_number,
                "configured_revision_limit": max_revisions,
                "evaluation_result": evaluation_result,
                "progression_state": "BLOCKED",
                "course_completion": "NOT_CLAIMED",
                "reason": reason,
            },
            connection=connection,
        )
    return True


def resolve_kickoff_revision_chain(
    db: Database,
    jobs: JobRepository,
    *,
    course_snapshot: dict[str, Any],
    preparation_job_id: str,
    preparation_artifact: dict[str, Any],
    initial_student_job_id: str,
    initial_examiner_job_id: str,
    gate_job_id: str,
    max_revisions: int,
    score_components: dict[str, float],
    base_priority: float,
    allow_schedule: bool,
) -> dict[str, Any]:
    """Resolve or extend an immutable, bounded kickoff revision chain.

    A successful return with ``passed=True`` identifies the exact examiner
    artifact that may become the first normal progression predecessor. Every
    other result explicitly leaves course completion unclaimed.
    """

    course_id = str(course_snapshot["course"]["course_id"])
    _supersede_legacy_revision_jobs(db, course_snapshot)
    groups = _revision_groups(
        db,
        course_id,
        source_id=str(course_snapshot["source"]["source_id"]),
        source_commit_hash=str(course_snapshot["source"]["commit_hash"]),
    )
    current_attempt = 1
    current_student_id = initial_student_job_id
    current_student_artifact = _verified_artifact(
        db, current_student_id, "student-course-attempt"
    )
    current_examiner_id = initial_examiner_job_id
    current_examiner_artifact = _verified_artifact(
        db, current_examiner_id, "independent-course-evaluation"
    )
    if current_student_artifact is None or current_examiner_artifact is None:
        return {
            "status": "KICKOFF_REVISION_EVIDENCE_INVALID",
            "reason": "kickoff examiner lacks current verified student or evaluation evidence",
            "course_completion": "NOT_CLAIMED",
            "created_jobs": 0,
            "scheduled": False,
        }
    evaluation_result = _evaluation_result(db, current_examiner_id)
    if evaluation_result is None:
        return {
            "status": "KICKOFF_REVISION_EVIDENCE_INVALID",
            "reason": "kickoff examiner lacks an attempt-bound control-plane evaluation",
            "course_completion": "NOT_CLAIMED",
            "created_jobs": 0,
            "scheduled": False,
        }

    while True:
        if evaluation_result == "PASS":
            if any(attempt > current_attempt for attempt in groups):
                return {
                    "status": "KICKOFF_REVISION_EVIDENCE_INVALID",
                    "reason": "a kickoff revision graph exists after an earlier passing attempt",
                    "course_completion": "NOT_CLAIMED",
                    "created_jobs": 0,
                    "scheduled": False,
                }
            return {
                "status": "KICKOFF_PASSED",
                "passed": True,
                "attempt_number": current_attempt,
                "examiner_job_id": current_examiner_id,
                "examiner_artifact": current_examiner_artifact,
                "course_completion": "NOT_CLAIMED",
                "created_jobs": 0,
                "scheduled": False,
            }
        if evaluation_result not in _NONPASSING_RESULTS:
            return {
                "status": "KICKOFF_REVISION_EVIDENCE_INVALID",
                "reason": f"unsupported kickoff evaluation result: {evaluation_result!r}",
                "course_completion": "NOT_CLAIMED",
                "created_jobs": 0,
                "scheduled": False,
            }
        next_attempt = current_attempt + 1
        candidate = _new_revision_snapshot(
            course_snapshot,
            attempt_number=next_attempt,
            preparation_job_id=preparation_job_id,
            preparation_artifact=preparation_artifact,
            prior_student_job_id=current_student_id,
            prior_student_artifact=current_student_artifact,
            prior_examiner_job_id=current_examiner_id,
            prior_examiner_artifact=current_examiner_artifact,
            prior_evaluation_result=evaluation_result,
        )
        expected_ids = _revision_job_ids(str(candidate["revision_id"]))
        group = groups.get(next_attempt)
        if group is None:
            if any(attempt > next_attempt for attempt in groups):
                return {
                    "status": "KICKOFF_REVISION_EVIDENCE_INVALID",
                    "reason": "non-contiguous kickoff revision sequence",
                    "course_completion": "NOT_CLAIMED",
                    "created_jobs": 0,
                    "scheduled": False,
                }
            if current_attempt - 1 >= max_revisions:
                recorded = _record_revision_block(
                    db,
                    course_snapshot,
                    attempt_number=current_attempt,
                    max_revisions=max_revisions,
                    evaluation_result=evaluation_result,
                )
                return {
                    "status": "BLOCKED_KICKOFF_REVISION_LIMIT_EXHAUSTED",
                    "progression_state": "BLOCKED",
                    "attempt_number": current_attempt,
                    "evaluation_result": evaluation_result,
                    "max_revisions": max_revisions,
                    "block_recorded": recorded,
                    "reason": (
                        "the latest independently evaluated kickoff attempt did not pass and "
                        "the configured finite revision limit is exhausted"
                    ),
                    "course_completion": "NOT_CLAIMED",
                    "created_jobs": 0,
                    "scheduled": False,
                }
            existing_roles: set[str] = set()
        else:
            error = _revision_snapshot_error(
                group["revision_snapshot"],
                course_snapshot=course_snapshot,
                expected=candidate,
            )
            if error is not None:
                return {
                    "status": "KICKOFF_REVISION_EVIDENCE_INVALID",
                    "reason": error,
                    "course_completion": "NOT_CLAIMED",
                    "created_jobs": 0,
                    "scheduled": False,
                }
            if any(
                job_id != expected_ids[role]
                for role, job_id in group["roles"].items()
            ):
                return {
                    "status": "KICKOFF_REVISION_EVIDENCE_INVALID",
                    "reason": "kickoff revision job ID does not match immutable evidence",
                    "course_completion": "NOT_CLAIMED",
                    "created_jobs": 0,
                    "scheduled": False,
                }
            existing_roles = set(group["roles"])

        if existing_roles != _REVISION_ROLES:
            if not allow_schedule:
                return {
                    "status": "DEFERRED_BY_LIMIT",
                    "phase": "kickoff_revision",
                    "attempt_number": next_attempt,
                    "evaluation_result": evaluation_result,
                    "course_completion": "NOT_CLAIMED",
                    "created_jobs": 0,
                    "scheduled": False,
                }
            identifiers, created = _ensure_revision_graph(
                jobs,
                course_snapshot,
                candidate,
                gate_job_id=gate_job_id,
                score_components=score_components,
                base_priority=base_priority,
            )
            return {
                "status": (
                    "KICKOFF_REVISION_GRAPH_SEEDED"
                    if not existing_roles
                    else "KICKOFF_PARTIAL_REVISION_GRAPH_REPAIRED"
                ),
                "revision_id": candidate["revision_id"],
                "attempt_number": next_attempt,
                "evaluation_result": evaluation_result,
                "jobs": identifiers,
                "created_jobs": created,
                "scheduled": True,
                "course_completion": "NOT_CLAIMED",
                "transfer_verification": "NOT_CLAIMED",
            }

        identifiers, unexpected_created = _ensure_revision_graph(
            jobs,
            course_snapshot,
            candidate,
            gate_job_id=gate_job_id,
            score_components=score_components,
            base_priority=base_priority,
        )
        if unexpected_created:
            raise RuntimeError("complete kickoff revision graph unexpectedly created jobs")
        student = jobs.get(identifiers["student_revision"])
        examiner = jobs.get(identifiers["examiner_revision"])
        if student is None or examiner is None:
            raise RuntimeError("kickoff revision graph disappeared during inspection")
        terminal = {
            role: job["state"]
            for role, job in (("student_revision", student), ("examiner_revision", examiner))
            if job["state"] in {"FAILED", "CANCELLED"}
        }
        if terminal:
            return {
                "status": "BLOCKED_KICKOFF_REVISION_PIPELINE_TERMINAL",
                "progression_state": "BLOCKED",
                "attempt_number": next_attempt,
                "role_states": terminal,
                "reason": "a required kickoff revision worker reached a terminal non-success state",
                "course_completion": "NOT_CLAIMED",
                "created_jobs": 0,
                "scheduled": False,
            }
        if examiner["state"] != "SUCCEEDED":
            return {
                "status": "WAITING_FOR_KICKOFF_REVISION_PIPELINE",
                "attempt_number": next_attempt,
                "role_states": {
                    "student_revision": student["state"],
                    "examiner_revision": examiner["state"],
                },
                "course_completion": "NOT_CLAIMED",
                "created_jobs": 0,
                "scheduled": False,
            }
        student_artifact = _verified_artifact(
            db, identifiers["student_revision"], "student-course-attempt"
        )
        examiner_artifact = _verified_artifact(
            db, identifiers["examiner_revision"], "independent-course-evaluation"
        )
        revision_result = _evaluation_result(db, identifiers["examiner_revision"])
        if student_artifact is None or examiner_artifact is None or revision_result is None:
            return {
                "status": "KICKOFF_REVISION_EVIDENCE_INVALID",
                "reason": (
                    f"kickoff revision attempt {next_attempt} lacks current verified, "
                    "attempt-bound student or examiner evidence"
                ),
                "course_completion": "NOT_CLAIMED",
                "created_jobs": 0,
                "scheduled": False,
            }
        current_attempt = next_attempt
        current_student_id = identifiers["student_revision"]
        current_student_artifact = student_artifact
        current_examiner_id = identifiers["examiner_revision"]
        current_examiner_artifact = examiner_artifact
        evaluation_result = revision_result


def authoritative_kickoff_revision_outcomes(
    connection: sqlite3.Connection,
    *,
    cohort_jobs: dict[str, dict[str, str]],
    initial_outcomes: dict[str, set[str]],
    examiner_outcomes: dict[str, str],
    gate_job_id: str,
) -> tuple[dict[str, set[str]], set[str]]:
    """Return latest outcomes only along one exact immutable kickoff chain.

    Courses without a kickoff-revision job retain their existing cohort outcome
    semantics. Once a revision exists, every completed ordinal must bind the
    exact prior student and examiner artifacts. Forks, gaps, conflicting
    snapshots, or evidence that cannot be tied to the declared ordinal are
    reported separately as invalid and never become a PASS claim.
    """

    resolved = {course_id: set(values) for course_id, values in initial_outcomes.items()}
    invalid: set[str] = set()
    rows = list(
        connection.execute(
            """
            SELECT job_id,type,worker_type,state,attempt_count,model,
                   reasoning_effort,payload_json
            FROM jobs ORDER BY created_at,job_id
            """
        )
    )
    revision_rows: dict[str, list[tuple[sqlite3.Row, dict[str, Any]]]] = {}
    for row in rows:
        payload = _decoded(row["payload_json"], dict, {})
        policy = payload.get("seed_policy")
        if not isinstance(policy, dict) or policy.get("kind") != KICKOFF_REVISION_POLICY_KIND:
            continue
        course_id = payload.get("course_id")
        if isinstance(course_id, str) and course_id:
            revision_rows.setdefault(course_id, []).append((row, payload))

    def artifact(job_id: str, expected_type: str) -> dict[str, Any] | None:
        matches = list(
            connection.execute(
                """
                SELECT a.artifact_id,a.type,a.checksum,a.attempt_number,
                       a.checksum_algorithm,a.integrity_status
                FROM jobs j JOIN artifacts a
                  ON a.job_id=j.job_id AND a.attempt_number=j.attempt_count
                WHERE j.job_id=? AND j.state='SUCCEEDED' AND a.type=?
                  AND a.checksum_algorithm='tree-sha256-v2'
                  AND a.integrity_status='VERIFIED_V2'
                ORDER BY a.created_at DESC,a.artifact_id DESC
                """,
                (job_id, expected_type),
            )
        )
        return dict(matches[0]) if len(matches) == 1 else None

    def dependencies(job_id: str) -> set[str]:
        return {
            str(item["depends_on_job_id"])
            for item in connection.execute(
                "SELECT depends_on_job_id FROM job_dependencies WHERE job_id=?",
                (job_id,),
            )
        }

    for course_id, raw_revisions in revision_rows.items():
        roles = cohort_jobs.get(course_id)
        if roles is None:
            # Reporting owns orphan accounting; an unrelated or inactive
            # course must not inflate active-cohort ambiguity metrics.
            continue
        if set(roles) != {"preparation", "student", "examiner"}:
            invalid.add(course_id)
            resolved.pop(course_id, None)
            continue
        preparation_id = roles["preparation"]
        initial_student_id = roles["student"]
        initial_examiner_id = roles["examiner"]
        preparation_row = next(
            (row for row in rows if row["job_id"] == preparation_id), None
        )
        if preparation_row is None:
            invalid.add(course_id)
            resolved.pop(course_id, None)
            continue
        preparation_payload = _decoded(preparation_row["payload_json"], dict, {})
        course_snapshot = preparation_payload.get("course_snapshot")
        if not isinstance(course_snapshot, dict):
            invalid.add(course_id)
            resolved.pop(course_id, None)
            continue
        source = course_snapshot.get("source")
        course = course_snapshot.get("course")
        if (
            not isinstance(source, dict)
            or not isinstance(course, dict)
            or course.get("course_id") != course_id
            or not isinstance(source.get("source_id"), str)
            or not isinstance(source.get("commit_hash"), str)
        ):
            invalid.add(course_id)
            resolved.pop(course_id, None)
            continue

        current_rows: list[tuple[sqlite3.Row, dict[str, Any]]] = []
        malformed_current = False
        for row, payload in raw_revisions:
            snapshot = payload.get("revision_snapshot")
            revision_source = snapshot.get("source") if isinstance(snapshot, dict) else None
            if not isinstance(revision_source, dict):
                malformed_current = True
                continue
            if (
                revision_source.get("source_id") == source["source_id"]
                and revision_source.get("commit_hash") == source["commit_hash"]
            ):
                current_rows.append((row, payload))
        if malformed_current:
            invalid.add(course_id)
            resolved.pop(course_id, None)
            continue
        if not current_rows:
            # Only historical source-revision graphs exist for this course.
            continue

        outcomes = initial_outcomes.get(course_id, set())
        preparation_artifact = artifact(preparation_id, "course-preparation")
        current_student_artifact = artifact(
            initial_student_id, "student-course-attempt"
        )
        current_examiner_artifact = artifact(
            initial_examiner_id, "independent-course-evaluation"
        )
        if (
            len(outcomes) != 1
            or preparation_artifact is None
            or current_student_artifact is None
            or current_examiner_artifact is None
        ):
            invalid.add(course_id)
            resolved.pop(course_id, None)
            continue

        groups: dict[int, dict[str, Any]] = {}
        group_invalid = False
        for row, payload in current_rows:
            policy = payload.get("seed_policy")
            attempt_number = policy.get("attempt_number") if isinstance(policy, dict) else None
            role = policy.get("role") if isinstance(policy, dict) else None
            if (
                not isinstance(policy, dict)
                or policy.get("version") != KICKOFF_REVISION_POLICY_VERSION
                or isinstance(attempt_number, bool)
                or not isinstance(attempt_number, int)
                or attempt_number < 2
                or role not in _REVISION_ROLES
            ):
                group_invalid = True
                break
            group = groups.setdefault(
                attempt_number,
                {"snapshot": payload.get("revision_snapshot"), "roles": {}},
            )
            if (
                group["snapshot"] != payload.get("revision_snapshot")
                or role in group["roles"]
            ):
                group_invalid = True
                break
            group["roles"][role] = (row, payload)
        if group_invalid:
            invalid.add(course_id)
            resolved.pop(course_id, None)
            continue

        current_attempt = 1
        current_student_id = initial_student_id
        current_examiner_id = initial_examiner_id
        evaluation_result = next(iter(outcomes))
        while True:
            if evaluation_result == "PASS":
                if any(attempt > current_attempt for attempt in groups):
                    group_invalid = True
                break
            if evaluation_result not in _NONPASSING_RESULTS:
                group_invalid = True
                break
            next_attempt = current_attempt + 1
            group = groups.get(next_attempt)
            if group is None:
                if any(attempt > next_attempt for attempt in groups):
                    group_invalid = True
                break
            candidate = _new_revision_snapshot(
                course_snapshot,
                attempt_number=next_attempt,
                preparation_job_id=preparation_id,
                preparation_artifact=preparation_artifact,
                prior_student_job_id=current_student_id,
                prior_student_artifact=current_student_artifact,
                prior_examiner_job_id=current_examiner_id,
                prior_examiner_artifact=current_examiner_artifact,
                prior_evaluation_result=evaluation_result,
            )
            if group["snapshot"] != candidate:
                group_invalid = True
                break
            expected_specs = _revision_graph_specs(
                course_snapshot, candidate, gate_job_id=gate_job_id
            )
            for role, (row, payload) in group["roles"].items():
                spec = expected_specs[role]
                if (
                    row["job_id"] != spec["job_id"]
                    or row["type"] != "codex_task"
                    or row["worker_type"] != spec["worker_type"]
                    or row["model"] != "gpt-5.6-sol"
                    or row["reasoning_effort"] != "ultra"
                    or not _kickoff_payloads_equivalent(
                        payload, spec["payload"]
                    )
                    or dependencies(str(row["job_id"])) != set(spec["dependencies"])
                ):
                    group_invalid = True
                    break
            if group_invalid:
                break
            if set(group["roles"]) != _REVISION_ROLES:
                if any(attempt > next_attempt for attempt in groups):
                    group_invalid = True
                break
            student_row, _ = group["roles"]["student_revision"]
            examiner_row, _ = group["roles"]["examiner_revision"]
            if (
                student_row["state"] != "SUCCEEDED"
                or examiner_row["state"] != "SUCCEEDED"
            ):
                if any(attempt > next_attempt for attempt in groups):
                    group_invalid = True
                break
            next_student_artifact = artifact(
                str(student_row["job_id"]), "student-course-attempt"
            )
            next_examiner_artifact = artifact(
                str(examiner_row["job_id"]), "independent-course-evaluation"
            )
            next_result = examiner_outcomes.get(str(examiner_row["job_id"]))
            if (
                next_student_artifact is None
                or next_examiner_artifact is None
                or next_result not in {"PASS", "REVISE", "FAIL"}
            ):
                group_invalid = True
                break
            current_attempt = next_attempt
            current_student_id = str(student_row["job_id"])
            current_student_artifact = next_student_artifact
            current_examiner_id = str(examiner_row["job_id"])
            current_examiner_artifact = next_examiner_artifact
            evaluation_result = next_result

        if group_invalid:
            invalid.add(course_id)
            resolved.pop(course_id, None)
        else:
            resolved[course_id] = {evaluation_result}
    return resolved, invalid
