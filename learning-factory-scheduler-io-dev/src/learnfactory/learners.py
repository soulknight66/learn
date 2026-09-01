from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .db import Database
from .publication import PublicationConnection
from .util import canonical_json, file_sha256, now


PERSONAS: dict[str, dict[str, Any]] = {
    "target": {
        "strengths": ["algorithms", "data structures", "competitive programming", "mathematical reasoning"],
        "growth_areas": [
            "production engineering", "large codebases", "architecture", "operations",
            "debugging", "deployment", "observability", "maintainability",
        ],
        "hint_policy": "Prefer diagnostic questions and production tradeoffs; skip elementary algorithm hints.",
    },
    "balanced": {
        "strengths": ["algorithms", "programming", "basic systems", "mathematics"],
        "growth_areas": ["advanced systems", "production reliability", "architecture"],
        "hint_policy": "Give conceptual hints before implementation details.",
    },
    "novice": {
        "strengths": ["basic programming"],
        "growth_areas": ["systems", "testing", "debugging", "architecture", "operations"],
        "hint_policy": "Use smaller steps, concrete examples, and early environment checks.",
    },
}


@dataclass(frozen=True)
class ExaminerEvaluation:
    """Strictly parsed, evidence-bearing output from an independent examiner."""

    result: str
    score: float
    evidence: tuple[str, ...]
    transfer_gaps: tuple[str, ...]
    checksum: str


@dataclass(frozen=True)
class _ConceptPolicy:
    concept: str
    description: str
    kind: str
    source_reference: str | None
    result_weights: dict[str, float]


@dataclass(frozen=True)
class _LearnerEvidencePolicy:
    student_id: str
    student_job_id: str
    student_artifact_type: str
    task_id: str
    task_type: str
    attempt_number: int
    evaluator: str
    evaluation_path: str
    schema_validator: str
    rubric: dict[str, Any]
    concepts: tuple[_ConceptPolicy, ...]


@dataclass(frozen=True)
class LearnerPublication:
    """Callbacks split across the authoritative commit boundary."""

    student_id: str
    on_publish: Callable[[PublicationConnection], None]
    on_commit: Callable[[], None]


def unambiguous_examiner_evaluation_result(
    connection: sqlite3.Connection, examiner_job_id: str
) -> str | None:
    """Return one policy-bound examiner result, or fail closed on ambiguity.

    ``evaluations`` intentionally permits more than one evaluator per attempt.
    Course progression, however, must never choose a winner by insertion time.
    Rows that claim the current examiner (or its policy evaluator) are usable
    only when every authoritative field is valid and semantically identical.
    The declared student dependency must also still have one current verified
    artifact for the exact physical job attempt recorded by the examiner hook.
    """

    job = connection.execute(
        """
        SELECT state,worker_type,attempt_count,payload_json
        FROM jobs WHERE job_id=?
        """,
        (examiner_job_id,),
    ).fetchone()
    if (
        job is None
        or job["state"] != "SUCCEEDED"
        or job["worker_type"] != "examiner"
        or isinstance(job["attempt_count"], bool)
        or not isinstance(job["attempt_count"], int)
        or job["attempt_count"] < 1
    ):
        return None
    try:
        payload = json.loads(str(job["payload_json"]))
        if not isinstance(payload, dict):
            return None
        policy = _parse_learner_evidence_policy(payload.get("learner_evidence"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None

    attempts = list(
        connection.execute(
            """
            SELECT attempt_id,task_type,result
            FROM attempts
            WHERE student_id=? AND task_id=? AND attempt_number=?
            """,
            (policy.student_id, policy.task_id, policy.attempt_number),
        )
    )
    if len(attempts) != 1 or attempts[0]["task_type"] != policy.task_type:
        return None
    attempt = attempts[0]

    student_rows = list(
        connection.execute(
            """
            SELECT student.attempt_count,student.payload_json,
                   artifact.artifact_id,artifact.type,artifact.checksum,
                   artifact.attempt_number,artifact.checksum_algorithm,
                   artifact.integrity_status
            FROM job_dependencies dependency
            JOIN jobs student ON student.job_id=dependency.depends_on_job_id
            JOIN artifacts artifact
              ON artifact.job_id=student.job_id
             AND artifact.attempt_number=student.attempt_count
            WHERE dependency.job_id=?
              AND dependency.depends_on_job_id=?
              AND student.state='SUCCEEDED'
              AND student.worker_type='student'
              AND artifact.type=?
              AND artifact.checksum_algorithm='tree-sha256-v2'
              AND artifact.integrity_status='VERIFIED_V2'
            """,
            (
                examiner_job_id,
                policy.student_job_id,
                policy.student_artifact_type,
            ),
        )
    )
    if len(student_rows) != 1:
        return None
    student = student_rows[0]
    try:
        student_payload = json.loads(str(student["payload_json"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if (
        not isinstance(student_payload, dict)
        or student_payload.get("student_id") != policy.student_id
        or student["attempt_number"] != student["attempt_count"]
    ):
        return None

    rows = list(
        connection.execute(
            """
            SELECT evaluator,rubric_json,result,score,evidence_json
            FROM evaluations WHERE attempt_id=?
            ORDER BY evaluation_id
            """,
            (attempt["attempt_id"],),
        )
    )
    authoritative: set[str] = set()
    resolved_result: str | None = None
    required_evidence = {
        "observations",
        "transfer_gaps",
        "evaluation_sha256",
        "examiner_job_id",
        "examiner_attempt",
        "student_job_id",
        "student_attempt",
        "schema_validator",
        "schema_validation_evidence",
    }
    for row in rows:
        try:
            evidence = json.loads(str(row["evidence_json"]))
            rubric = json.loads(str(row["rubric_json"]))
        except (TypeError, ValueError, json.JSONDecodeError):
            # A corrupt row cannot claim this examiner safely.  If its evaluator
            # name collides with the policy, it is contradictory evidence.
            if row["evaluator"] == policy.evaluator:
                return None
            continue
        if not isinstance(evidence, dict):
            if row["evaluator"] == policy.evaluator:
                return None
            continue
        claims_examiner = evidence.get("examiner_job_id") == examiner_job_id
        claims_evaluator = row["evaluator"] == policy.evaluator
        if not claims_examiner and not claims_evaluator:
            continue
        result = row["result"]
        score = row["score"]
        sha256 = evidence.get("evaluation_sha256")
        student_attempt = evidence.get("student_attempt")
        examiner_attempt = evidence.get("examiner_attempt")
        if (
            not claims_examiner
            or not claims_evaluator
            or not isinstance(rubric, dict)
            or rubric != policy.rubric
            or result not in {"PASS", "REVISE", "FAIL"}
            or attempt["result"] != result
            or isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
            or not 0 <= float(score) <= 100
            or set(evidence) != required_evidence
            or isinstance(examiner_attempt, bool)
            or examiner_attempt != job["attempt_count"]
            or evidence.get("student_job_id") != policy.student_job_id
            or isinstance(student_attempt, bool)
            or student_attempt != student["attempt_count"]
            or evidence.get("schema_validator") != policy.schema_validator
            or not isinstance(evidence.get("schema_validation_evidence"), dict)
            or not isinstance(sha256, str)
            or len(sha256) != 64
            or any(character not in "0123456789abcdef" for character in sha256)
        ):
            return None
        try:
            _nonempty_string_array(
                evidence.get("observations"), "observations", required=True
            )
            _nonempty_string_array(
                evidence.get("transfer_gaps"), "transfer_gaps", required=False
            )
        except ValueError:
            return None
        bundle = canonical_json(
            {
                "evaluator": row["evaluator"],
                "rubric": rubric,
                "result": result,
                "score": float(score),
                "evidence": evidence,
            }
        )
        authoritative.add(bundle)
        resolved_result = str(result)
    if len(authoritative) != 1:
        return None
    return resolved_result


def seed_students(db: Database, warehouse: Path) -> list[str]:
    identifiers: list[str] = []
    with db.transaction(immediate=True) as connection:
        for persona, profile in PERSONAS.items():
            identifier = f"student-{persona}"
            connection.execute(
                """
                INSERT OR IGNORE INTO students(student_id,persona,profile_json,created_at,current_state_json)
                VALUES (?,?,?,?,?)
                """,
                (identifier, persona, canonical_json(profile), now(), canonical_json({"status": "READY"})),
            )
            identifiers.append(identifier)
    for identifier in identifiers:
        persona = identifier.removeprefix("student-")
        root = warehouse / "learners" / identifier
        root.mkdir(parents=True, exist_ok=True)
        profile = PERSONAS[persona]
        (root / "PROFILE.yaml").write_text(_profile_yaml(identifier, persona, profile), encoding="utf-8")
        _write_if_missing(root / "KNOWLEDGE.json", {"student_id": identifier, "concepts": []})
        _write_text_if_missing(root / "MISTAKES.md", "# Recurring mistakes\n\nNo evidence recorded yet.\n")
        _write_text_if_missing(root / "EXPERIENCE.md", "# Learning experience\n\n")
        _write_if_missing(root / "PROJECTS.json", {"student_id": identifier, "projects": []})
        _write_if_missing(root / "CURRENT_STATE.json", {"status": "READY", "active_attempt": None})
    return identifiers


def add_knowledge_evidence(
    db: Database,
    student_id: str,
    concept: str,
    description: str,
    *,
    kind: str,
    source_reference: str | None,
    weight: float,
) -> float:
    """Update confidence from weighted external evidence, preserving every observation."""
    from .util import new_id

    with db.transaction(immediate=True) as connection:
        current = connection.execute(
            "SELECT confidence FROM learner_knowledge WHERE student_id=? AND concept=?",
            (student_id, concept),
        ).fetchone()
        old = float(current["confidence"]) if current else 0.5
        bounded_weight = max(-1.0, min(1.0, weight))
        confidence = max(0.0, min(1.0, old + bounded_weight * (1.0 - old if bounded_weight > 0 else old) * 0.25))
        connection.execute(
            """
            INSERT INTO learner_knowledge(student_id,concept,confidence,misconceptions_json,last_updated)
            VALUES (?,?,?,?,?)
            ON CONFLICT(student_id,concept) DO UPDATE SET confidence=excluded.confidence,last_updated=excluded.last_updated
            """,
            (student_id, concept, confidence, "[]", now()),
        )
        connection.execute(
            """
            INSERT INTO knowledge_evidence(
                evidence_id,student_id,concept,kind,description,source_reference,weight,created_at
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (new_id("evidence"), student_id, concept, kind, description, source_reference, weight, now()),
        )
    return confidence


def prepare_examiner_learner_publication(
    db: Database,
    warehouse: Path,
    *,
    examiner_job_id: str,
    examiner_attempt: int,
    worker_type: str,
    payload: dict[str, Any],
    workspace: Path,
) -> LearnerPublication | None:
    """Prepare learner activation without changing authoritative state.

    Only an examiner job with an explicit control-plane policy is eligible. The
    worker controls the observations in ``evaluation.json``; it does not control
    learner identity, task identity, concept names, evidence weights, or rubric.
    The returned database callback must be invoked by the fenced artifact
    publication transaction. The file callback is deliberately separate because
    learner files are derived views and must never get ahead of that transaction.
    """

    raw_policy = payload.get("learner_evidence")
    if raw_policy is None:
        return None
    if worker_type != "examiner":
        raise ValueError("learner evidence may only be activated by an examiner worker")
    if isinstance(examiner_attempt, bool) or not isinstance(examiner_attempt, int) or examiner_attempt < 1:
        raise ValueError("examiner attempt must be a positive integer")
    policy = _parse_learner_evidence_policy(raw_policy)
    if policy.student_job_id == examiner_job_id:
        raise ValueError("examiner and student jobs must be distinct")
    _require_matching_schema_validator(payload, policy)
    evaluation_file = workspace / _safe_evaluation_path(policy.evaluation_path)
    evaluation = parse_examiner_evaluation(evaluation_file)

    def activate(connection: PublicationConnection) -> None:
        if not connection.in_transaction:
            raise ValueError("learner activation requires the publication transaction")
        if (
            evaluation_file.is_symlink()
            or not evaluation_file.is_file()
            or file_sha256(evaluation_file) != evaluation.checksum
        ):
            raise ValueError("examiner evaluation changed after deterministic parsing")
        context = _validated_student_attempt_context(
            connection,
            examiner_job_id=examiner_job_id,
            examiner_attempt=examiner_attempt,
            policy=policy,
        )
        validation_evidence = json.loads(context["validation_evidence_json"])
        description_suffix = (
            f" Independent examiner result {evaluation.result} with score "
            f"{evaluation.score:g}. Observations: " + " | ".join(evaluation.evidence)
        )
        concepts = [
            {
                "concept": item.concept,
                "description": item.description + description_suffix,
                "kind": item.kind,
                "source_reference": item.source_reference,
                "weight": item.result_weights[evaluation.result],
            }
            for item in policy.concepts
        ]
        activate_validated_attempt(
            db,
            connection,
            student_id=policy.student_id,
            task_id=policy.task_id,
            task_type=policy.task_type,
            attempt_number=policy.attempt_number,
            start_time=float(context["started_at"]),
            end_time=float(context["finished_at"]),
            result=evaluation.result,
            workspace=str(context["artifact_path"]),
            evaluator=policy.evaluator,
            rubric=policy.rubric,
            score=evaluation.score,
            evaluation_evidence={
                "observations": list(evaluation.evidence),
                "transfer_gaps": list(evaluation.transfer_gaps),
                "evaluation_sha256": evaluation.checksum,
                "examiner_job_id": examiner_job_id,
                "examiner_attempt": examiner_attempt,
                "student_job_id": policy.student_job_id,
                "student_attempt": int(context["student_attempt"]),
                "schema_validator": policy.schema_validator,
                "schema_validation_evidence": validation_evidence,
            },
            concepts=concepts,
            evaluated_at=now(),
        )

    def render_after_commit() -> None:
        sync_student_memory(db, warehouse, policy.student_id)

    return LearnerPublication(policy.student_id, activate, render_after_commit)


def parse_examiner_evaluation(path: Path) -> ExaminerEvaluation:
    """Parse the narrow examiner contract without permissive Python coercions."""

    if path.is_symlink() or not path.is_file():
        raise ValueError("examiner evaluation JSON is missing or is not a regular file")
    try:
        encoded = path.read_bytes()
        if len(encoded) > 1024 * 1024:
            raise ValueError("examiner evaluation JSON exceeds the 1 MiB limit")
        raw = json.loads(
            encoded.decode("utf-8"), parse_constant=_reject_json_constant
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"invalid examiner evaluation JSON: {error}") from error
    if not isinstance(raw, dict):
        raise ValueError("examiner evaluation must be a JSON object")
    required = {"result", "score", "evidence", "transfer_gaps"}
    if set(raw) != required:
        missing = sorted(required - set(raw))
        extra = sorted(set(raw) - required)
        raise ValueError(
            f"examiner evaluation fields do not match contract; missing={missing}, extra={extra}"
        )
    result = raw["result"]
    if not isinstance(result, str) or result not in {"PASS", "REVISE", "FAIL"}:
        raise ValueError("examiner result must be PASS, REVISE, or FAIL")
    score = raw["score"]
    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(score)
        or not 0 <= score <= 100
    ):
        raise ValueError("examiner score must be a finite number from 0 through 100")
    evidence = _nonempty_string_array(raw["evidence"], "evidence", required=True)
    transfer_gaps = _nonempty_string_array(
        raw["transfer_gaps"], "transfer_gaps", required=False
    )
    return ExaminerEvaluation(
        result,
        float(score),
        evidence,
        transfer_gaps,
        hashlib.sha256(encoded).hexdigest(),
    )


def _parse_learner_evidence_policy(raw: object) -> _LearnerEvidencePolicy:
    if not isinstance(raw, dict):
        raise ValueError("learner_evidence must be an object")
    required = {
        "schema_version",
        "student_id",
        "student_job_id",
        "student_artifact_type",
        "task_id",
        "task_type",
        "attempt_number",
        "evaluator",
        "evaluation_path",
        "schema_validator",
        "rubric",
        "concepts",
    }
    if set(raw) != required:
        raise ValueError("learner_evidence fields do not match the versioned contract")
    if raw["schema_version"] != 1 or isinstance(raw["schema_version"], bool):
        raise ValueError("unsupported learner_evidence schema_version")
    text_fields: dict[str, str] = {}
    for name in (
        "student_id",
        "student_job_id",
        "student_artifact_type",
        "task_id",
        "task_type",
        "evaluator",
        "evaluation_path",
        "schema_validator",
    ):
        value = raw[name]
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"learner_evidence {name} must be a normalized nonempty string")
        text_fields[name] = value
    rubric = raw["rubric"]
    if not isinstance(rubric, dict) or not rubric:
        raise ValueError("learner_evidence rubric must be a nonempty object")
    attempt_number = raw["attempt_number"]
    if (
        isinstance(attempt_number, bool)
        or not isinstance(attempt_number, int)
        or attempt_number < 1
    ):
        raise ValueError("learner_evidence attempt_number must be a positive integer")
    raw_concepts = raw["concepts"]
    if not isinstance(raw_concepts, list) or not raw_concepts:
        raise ValueError("learner_evidence concepts must be a nonempty array")
    concepts: list[_ConceptPolicy] = []
    seen: set[str] = set()
    for index, raw_concept in enumerate(raw_concepts):
        if not isinstance(raw_concept, dict) or set(raw_concept) != {
            "concept",
            "description",
            "kind",
            "source_reference",
            "result_weights",
        }:
            raise ValueError(f"learner_evidence concept {index} has an invalid shape")
        values: dict[str, str] = {}
        for name in ("concept", "description", "kind"):
            value = raw_concept[name]
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"learner_evidence concept {index} {name} is invalid")
            values[name] = value
        if values["concept"] in seen:
            raise ValueError("learner_evidence concept names must be unique")
        seen.add(values["concept"])
        source_reference = raw_concept["source_reference"]
        if source_reference is not None and (
            not isinstance(source_reference, str)
            or not source_reference.strip()
            or source_reference != source_reference.strip()
        ):
            raise ValueError("learner_evidence source_reference is invalid")
        raw_weights = raw_concept["result_weights"]
        if not isinstance(raw_weights, dict) or set(raw_weights) != {
            "PASS",
            "REVISE",
            "FAIL",
        }:
            raise ValueError("learner_evidence result_weights must cover every result")
        weights: dict[str, float] = {}
        for result, raw_weight in raw_weights.items():
            if (
                isinstance(raw_weight, bool)
                or not isinstance(raw_weight, (int, float))
                or not math.isfinite(raw_weight)
                or not -1 <= raw_weight <= 1
            ):
                raise ValueError("learner_evidence weights must be finite numbers from -1 through 1")
            weights[result] = float(raw_weight)
        concepts.append(
            _ConceptPolicy(
                values["concept"],
                values["description"],
                values["kind"],
                source_reference,
                weights,
            )
        )
    return _LearnerEvidencePolicy(
        text_fields["student_id"],
        text_fields["student_job_id"],
        text_fields["student_artifact_type"],
        text_fields["task_id"],
        text_fields["task_type"],
        attempt_number,
        text_fields["evaluator"],
        text_fields["evaluation_path"],
        text_fields["schema_validator"],
        dict(rubric),
        tuple(concepts),
    )


def _require_matching_schema_validator(
    payload: dict[str, Any], policy: _LearnerEvidencePolicy
) -> None:
    output_schema = payload.get("output_schema")
    validators = payload.get("validators")
    if not isinstance(output_schema, dict) or not isinstance(validators, list):
        raise ValueError("examiner learner evidence requires an output schema and validators")
    matches = [
        item
        for item in validators
        if isinstance(item, dict)
        and item.get("type") == "json_schema"
        and item.get("name") == policy.schema_validator
        and item.get("path") == policy.evaluation_path
        and item.get("schema") == output_schema
    ]
    if len(matches) != 1:
        raise ValueError(
            "examiner learner evidence requires exactly one matching JSON-schema validator"
        )


def _validated_student_attempt_context(
    connection: PublicationConnection,
    *,
    examiner_job_id: str,
    examiner_attempt: int,
    policy: _LearnerEvidencePolicy,
) -> dict[str, Any]:
    validation = connection.execute(
        """
        SELECT evidence_json
        FROM validations
        WHERE job_id=? AND attempt_number=? AND validator=? AND status='PASS'
        ORDER BY finished_at DESC,validation_id DESC
        LIMIT 1
        """,
        (examiner_job_id, examiner_attempt, policy.schema_validator),
    ).fetchone()
    if validation is None:
        raise ValueError("examiner schema validation has not passed for this attempt")
    try:
        validation_evidence = json.loads(validation["evidence_json"])
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("examiner schema validation evidence is corrupt") from error
    if not isinstance(validation_evidence, dict):
        raise ValueError("examiner schema validation evidence must be an object")
    student = connection.execute(
        """
        SELECT student.attempt_count AS student_attempt,
               COALESCE(run.started_at,student.started_at) AS started_at,
               COALESCE(run.finished_at,student.finished_at) AS finished_at,
               artifact.path AS artifact_path
        FROM job_dependencies dependency
        JOIN jobs student ON student.job_id=dependency.depends_on_job_id
        JOIN artifacts artifact
          ON artifact.job_id=student.job_id
         AND artifact.attempt_number=student.attempt_count
        LEFT JOIN job_runs run
          ON run.job_id=student.job_id
         AND run.attempt_number=student.attempt_count
        WHERE dependency.job_id=?
          AND dependency.depends_on_job_id=?
          AND student.state='SUCCEEDED'
          AND student.worker_type='student'
          AND artifact.type=?
          AND artifact.checksum_algorithm='tree-sha256-v2'
          AND artifact.integrity_status='VERIFIED_V2'
        ORDER BY artifact.created_at DESC,run.started_at DESC
        LIMIT 1
        """,
        (
            examiner_job_id,
            policy.student_job_id,
            policy.student_artifact_type,
        ),
    ).fetchone()
    if student is None:
        raise ValueError(
            "examiner learner evidence lacks a successful, declared student artifact dependency"
        )
    started = student["started_at"]
    finished = student["finished_at"]
    if not _finite_number(started) or not _finite_number(finished) or finished < started:
        raise ValueError("student attempt timestamps are unavailable or invalid")
    return {
        "student_attempt": student["student_attempt"],
        "started_at": started,
        "finished_at": finished,
        "artifact_path": student["artifact_path"],
        "validation_evidence_json": canonical_json(validation_evidence),
    }


def _safe_evaluation_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("examiner evaluation path must be a safe relative path")
    return path


def _nonempty_string_array(
    raw: object, name: str, *, required: bool
) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise ValueError(f"examiner {name} must be an array")
    if required and not raw:
        raise ValueError(f"examiner {name} must contain concrete observations")
    if len(raw) > 100:
        raise ValueError(f"examiner {name} contains too many entries")
    values: list[str] = []
    for item in raw:
        if (
            not isinstance(item, str)
            or not item.strip()
            or item != item.strip()
            or len(item) > 4000
        ):
            raise ValueError(f"examiner {name} entries must be normalized nonempty strings")
        values.append(item)
    return tuple(values)


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def record_validated_attempt(
    db: Database,
    warehouse: Path,
    *,
    student_id: str,
    task_id: str,
    task_type: str,
    attempt_number: int,
    start_time: float,
    end_time: float,
    result: str,
    workspace: str,
    evaluator: str,
    rubric: dict[str, Any],
    score: float | None,
    evaluation_evidence: dict[str, Any],
    concepts: list[dict[str, Any]],
    evaluated_at: float | None = None,
) -> str:
    """Idempotently record externally validated learner evidence and refresh its files."""

    with db.transaction(immediate=True) as connection:
        stored_attempt = activate_validated_attempt(
            db,
            connection,
            student_id=student_id,
            task_id=task_id,
            task_type=task_type,
            attempt_number=attempt_number,
            start_time=start_time,
            end_time=end_time,
            result=result,
            workspace=workspace,
            evaluator=evaluator,
            rubric=rubric,
            score=score,
            evaluation_evidence=evaluation_evidence,
            concepts=concepts,
            evaluated_at=evaluated_at,
        )
    sync_student_memory(db, warehouse, student_id)
    return stored_attempt


def activate_validated_attempt(
    db: Database,
    connection: PublicationConnection,
    *,
    student_id: str,
    task_id: str,
    task_type: str,
    attempt_number: int,
    start_time: float,
    end_time: float,
    result: str,
    workspace: str,
    evaluator: str,
    rubric: dict[str, Any],
    score: float | None,
    evaluation_evidence: dict[str, Any],
    concepts: list[dict[str, Any]],
    evaluated_at: float | None = None,
) -> str:
    """Activate evidence using the caller's already-open publication transaction."""

    if not connection.in_transaction:
        raise ValueError("validated attempt activation requires an open transaction")
    normalized = _validated_attempt_input(
        student_id=student_id,
        task_id=task_id,
        task_type=task_type,
        attempt_number=attempt_number,
        start_time=start_time,
        end_time=end_time,
        result=result,
        workspace=workspace,
        evaluator=evaluator,
        rubric=rubric,
        score=score,
        evaluation_evidence=evaluation_evidence,
        concepts=concepts,
        evaluated_at=evaluated_at,
    )
    evaluated = normalized["evaluated_at"]
    attempt_id = _stable_evidence_id(
        "attempt", student_id, task_id, str(attempt_number)
    )
    evaluation_id = _stable_evidence_id("evaluation", attempt_id, evaluator)
    student = connection.execute(
        "SELECT student_id FROM students WHERE student_id=?", (student_id,)
    ).fetchone()
    if student is None:
        raise ValueError(f"unknown student: {student_id}")
    connection.execute(
        """
        INSERT INTO attempts(
            attempt_id,student_id,task_id,task_type,attempt_number,start_time,
            end_time,result,workspace
        ) VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(student_id,task_id,attempt_number) DO UPDATE SET
            end_time=excluded.end_time,result=excluded.result,workspace=excluded.workspace
        """,
        (
            attempt_id, student_id, task_id, task_type, attempt_number,
            start_time, end_time, result, workspace,
        ),
    )
    stored_attempt = connection.execute(
        """
        SELECT attempt_id FROM attempts
        WHERE student_id=? AND task_id=? AND attempt_number=?
        """,
        (student_id, task_id, attempt_number),
    ).fetchone()["attempt_id"]
    connection.execute(
        """
        INSERT INTO evaluations(
            evaluation_id,attempt_id,evaluator,rubric_json,result,score,
            evidence_json,created_at
        ) VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(evaluation_id) DO UPDATE SET
            rubric_json=excluded.rubric_json,result=excluded.result,
            score=excluded.score,evidence_json=excluded.evidence_json
        """,
        (
            evaluation_id, stored_attempt, evaluator, canonical_json(rubric),
            result, score, canonical_json(evaluation_evidence), evaluated,
        ),
    )
    for observation in normalized["concepts"]:
        concept = str(observation["concept"]).strip()
        description = str(observation["description"]).strip()
        kind = str(observation.get("kind", "validated-attempt")).strip()
        source_reference = observation.get("source_reference")
        weight = float(observation.get("weight", 0))
        misconceptions = list(observation.get("misconceptions", []))
        evidence_id = _stable_evidence_id(
            "evidence", stored_attempt, concept, kind, description
        )
        existing = connection.execute(
            "SELECT confidence,misconceptions_json FROM learner_knowledge WHERE student_id=? AND concept=?",
            (student_id, concept),
        ).fetchone()
        if existing is None:
            old_confidence = 0.5
            known_misconceptions: set[str] = set()
            connection.execute(
                """
                INSERT INTO learner_knowledge(
                    student_id,concept,confidence,misconceptions_json,last_updated
                ) VALUES (?,?,?,?,?)
                """,
                (student_id, concept, old_confidence, "[]", end_time),
            )
        else:
            old_confidence = float(existing["confidence"])
            known_misconceptions = set(json.loads(existing["misconceptions_json"]))
        inserted = connection.execute(
            """
            INSERT OR IGNORE INTO knowledge_evidence(
                evidence_id,student_id,concept,kind,description,source_reference,
                weight,created_at
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                evidence_id, student_id, concept, kind, description,
                str(source_reference) if source_reference is not None else None,
                weight, end_time,
            ),
        )
        if inserted.rowcount:
            confidence = _updated_confidence(old_confidence, weight)
        else:
            confidence = old_confidence
        connection.execute(
            """
            INSERT INTO learner_knowledge(
                student_id,concept,confidence,misconceptions_json,last_updated
            ) VALUES (?,?,?,?,?)
            ON CONFLICT(student_id,concept) DO UPDATE SET
                confidence=excluded.confidence,
                misconceptions_json=excluded.misconceptions_json,
                last_updated=excluded.last_updated
            """,
            (
                student_id, concept, confidence,
                canonical_json(sorted(known_misconceptions | set(misconceptions))),
                end_time,
            ),
        )
    connection.execute(
        "UPDATE students SET current_state_json=? WHERE student_id=?",
        (
            canonical_json(
                {
                    "status": "READY",
                    "active_attempt": None,
                    "last_completed_attempt": stored_attempt,
                }
            ),
            student_id,
        ),
    )
    db.emit_event(
        "learner-model",
        "LEARNER_ATTEMPT_RECORDED",
        payload={
            "student_id": student_id,
            "attempt_id": stored_attempt,
            "task_id": task_id,
            "result": result,
            "concepts": [str(item["concept"]) for item in normalized["concepts"]],
        },
        connection=connection,
    )
    return str(stored_attempt)


def sync_student_memory(db: Database, warehouse: Path, student_id: str) -> None:
    """Render the authoritative learner model into a human-inspectable directory."""

    with db.transaction() as connection:
        student = connection.execute(
            "SELECT persona,profile_json,current_state_json FROM students WHERE student_id=?",
            (student_id,),
        ).fetchone()
        if student is None:
            raise ValueError(f"unknown student: {student_id}")
        knowledge_rows = list(
            connection.execute(
                """
                SELECT concept,confidence,misconceptions_json,last_updated
                FROM learner_knowledge WHERE student_id=? ORDER BY concept
                """,
                (student_id,),
            )
        )
        evidence_rows = list(
            connection.execute(
                """
                SELECT evidence_id,concept,kind,description,source_reference,weight,created_at
                FROM knowledge_evidence WHERE student_id=? ORDER BY created_at,evidence_id
                """,
                (student_id,),
            )
        )
        attempts = [
            dict(row)
            for row in connection.execute(
                """
                SELECT attempt_id,task_id,task_type,attempt_number,start_time,end_time,result,workspace
                FROM attempts WHERE student_id=? ORDER BY start_time,attempt_number
                """,
                (student_id,),
            )
        ]
        evaluations = {
            row["attempt_id"]: {
                "evaluator": row["evaluator"],
                "result": row["result"],
                "score": row["score"],
                "evidence": json.loads(row["evidence_json"]),
            }
            for row in connection.execute(
                """
                SELECT attempt_id,evaluator,result,score,evidence_json
                FROM evaluations WHERE attempt_id IN (
                    SELECT attempt_id FROM attempts WHERE student_id=?
                ) ORDER BY created_at
                """,
                (student_id,),
            )
        }
    by_concept: dict[str, list[dict[str, Any]]] = {}
    for row in evidence_rows:
        by_concept.setdefault(row["concept"], []).append(dict(row))
    concepts = [
        {
            "concept": row["concept"],
            "confidence": row["confidence"],
            "misconceptions": json.loads(row["misconceptions_json"]),
            "last_updated": row["last_updated"],
            "evidence": by_concept.get(row["concept"], []),
        }
        for row in knowledge_rows
    ]
    root = warehouse / "learners" / student_id
    root.mkdir(parents=True, exist_ok=True)
    profile = json.loads(student["profile_json"])
    (root / "PROFILE.yaml").write_text(
        _profile_yaml(student_id, student["persona"], profile), encoding="utf-8"
    )
    _write_json(root / "KNOWLEDGE.json", {"student_id": student_id, "concepts": concepts})
    _write_json(root / "PROJECTS.json", {"student_id": student_id, "projects": attempts})
    _write_json(root / "CURRENT_STATE.json", json.loads(student["current_state_json"]))
    mistake_lines = ["# Recurring mistakes", ""]
    for item in concepts:
        for misconception in item["misconceptions"]:
            mistake_lines.append(f"- **{item['concept']}**: {misconception}")
    if len(mistake_lines) == 2:
        mistake_lines.append("No misconception evidence recorded yet.")
    (root / "MISTAKES.md").write_text("\n".join(mistake_lines) + "\n", encoding="utf-8")
    experience_lines = ["# Learning experience", ""]
    for attempt in attempts:
        evaluation = evaluations.get(attempt["attempt_id"])
        experience_lines.extend(
            [
                f"## {attempt['task_id']} / attempt {attempt['attempt_number']}",
                "",
                f"- Result: {attempt['result']}",
                f"- Type: {attempt['task_type']}",
                f"- Artifact: `{attempt['workspace']}`",
                f"- Evaluator: {evaluation['evaluator'] if evaluation else 'not recorded'}",
                f"- Score: {evaluation['score'] if evaluation else 'not recorded'}",
                "",
            ]
        )
    (root / "EXPERIENCE.md").write_text(
        "\n".join(experience_lines).rstrip() + "\n", encoding="utf-8"
    )


def _validated_attempt_input(**values: Any) -> dict[str, Any]:
    for name in ("student_id", "task_id", "task_type", "result", "workspace", "evaluator"):
        value = values[name]
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"{name} must be a normalized nonempty string")
    if values["result"] not in {"PASS", "REVISE", "FAIL"}:
        raise ValueError("attempt result must be PASS, REVISE, or FAIL")
    attempt_number = values["attempt_number"]
    if isinstance(attempt_number, bool) or not isinstance(attempt_number, int) or attempt_number < 1:
        raise ValueError("attempt number must be a positive integer")
    start_time = values["start_time"]
    end_time = values["end_time"]
    if not _finite_number(start_time) or not _finite_number(end_time) or end_time < start_time:
        raise ValueError("attempt timestamps must be finite and ordered")
    score = values["score"]
    if score is not None and (
        not _finite_number(score) or not 0 <= score <= 100
    ):
        raise ValueError("evaluation score must be null or a finite number from 0 through 100")
    rubric = values["rubric"]
    evaluation_evidence = values["evaluation_evidence"]
    if not isinstance(rubric, dict) or not rubric:
        raise ValueError("evaluation rubric must be a nonempty object")
    if not isinstance(evaluation_evidence, dict) or not evaluation_evidence:
        raise ValueError("evaluation evidence must be a nonempty object")
    raw_concepts = values["concepts"]
    if not isinstance(raw_concepts, list) or not raw_concepts:
        raise ValueError("validated attempt requires concept evidence")
    concepts: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_concepts):
        if not isinstance(raw, dict):
            raise ValueError(f"concept evidence {index} must be an object")
        concept = raw.get("concept")
        description = raw.get("description")
        kind = raw.get("kind", "validated-attempt")
        if not isinstance(concept, str) or not concept.strip() or concept != concept.strip():
            raise ValueError(f"concept evidence {index} has an invalid concept")
        if (
            not isinstance(description, str)
            or not description.strip()
            or description != description.strip()
        ):
            raise ValueError(f"concept evidence {index} has an invalid description")
        if not isinstance(kind, str) or not kind.strip() or kind != kind.strip():
            raise ValueError(f"concept evidence {index} has an invalid kind")
        source_reference = raw.get("source_reference")
        if source_reference is not None and (
            not isinstance(source_reference, str)
            or not source_reference.strip()
            or source_reference != source_reference.strip()
        ):
            raise ValueError(f"concept evidence {index} has an invalid source reference")
        weight = raw.get("weight", 0)
        if not _finite_number(weight) or not -1 <= weight <= 1:
            raise ValueError(f"concept evidence {index} has an invalid weight")
        misconceptions = raw.get("misconceptions", [])
        if not isinstance(misconceptions, list) or any(
            not isinstance(item, str)
            or not item.strip()
            or item != item.strip()
            for item in misconceptions
        ):
            raise ValueError(f"concept evidence {index} has invalid misconceptions")
        concepts.append(
            {
                "concept": concept,
                "description": description,
                "kind": kind,
                "source_reference": source_reference,
                "weight": float(weight),
                "misconceptions": sorted(set(misconceptions)),
            }
        )
    evaluated_at = values["evaluated_at"]
    if evaluated_at is None:
        evaluated_at = float(end_time)
    if not _finite_number(evaluated_at) or evaluated_at < end_time:
        raise ValueError("evaluation timestamp must be finite and not predate the attempt")
    return {**values, "concepts": concepts, "evaluated_at": float(evaluated_at)}


def _finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _updated_confidence(old: float, weight: float) -> float:
    return max(
        0.0,
        min(1.0, old + weight * (1.0 - old if weight > 0 else old) * 0.25),
    )


def _stable_evidence_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()[:32]
    return f"{prefix}_{digest}"


def _write_if_missing(path: Path, value: Any) -> None:
    if not path.exists():
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_text_if_missing(path: Path, value: str) -> None:
    if not path.exists():
        path.write_text(value, encoding="utf-8")


def _profile_yaml(identifier: str, persona: str, profile: dict[str, Any]) -> str:
    lines = [f"student_id: {identifier}", f"persona: {persona}", "strengths:"]
    lines.extend(f"  - {item}" for item in profile["strengths"])
    lines.append("growth_areas:")
    lines.extend(f"  - {item}" for item in profile["growth_areas"])
    lines.append(f"hint_policy: {json.dumps(profile['hint_policy'])}")
    return "\n".join(lines) + "\n"
