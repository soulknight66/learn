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


@dataclass(frozen=True)
class _LegacyEvidenceInvalidationTarget:
    evidence_id: str
    invalidation_id: str


@dataclass(frozen=True)
class _LegacyAttemptInvalidationTarget:
    attempt_id: str
    examiner_job_id: str
    student_id: str
    task_id: str
    invalidate_attempt: bool
    evidence: tuple[_LegacyEvidenceInvalidationTarget, ...]


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
        submission_contract = _submission_contract_for_examiner(payload, policy)
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
                   artifact.artifact_id AS artifact_id,
                   artifact.type AS artifact_type,
                   artifact.checksum AS artifact_checksum,
                   artifact.attempt_number AS artifact_attempt,
                   artifact.checksum_algorithm AS artifact_checksum_algorithm,
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
        or student["artifact_attempt"] != student["attempt_count"]
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
    authoritative_submission: dict[str, Any] | None = None
    if submission_contract is not None:
        authoritative_submission = _authoritative_submission_binding(
            connection,
            examiner_job_id=examiner_job_id,
            examiner_attempt=int(job["attempt_count"]),
            contract=submission_contract,
            student=student,
        )
        if authoritative_submission is None:
            return None
        required_evidence.add("student_submission_binding")
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
            or (
                authoritative_submission is not None
                and evidence.get("student_submission_binding")
                != authoritative_submission
            )
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


def _submission_contract_for_examiner(
    payload: dict[str, Any], policy: _LearnerEvidencePolicy
) -> object | None:
    """Require the hardened handoff for every CSDIY examiner path.

    Legacy kickoff, kickoff-revision, unit, and unit-revision verdicts remain
    durable history, but cannot become authoritative learner or progression
    evidence because they never saw the complete learner artifact tree.
    """

    seed_policy = payload.get("seed_policy")
    role = seed_policy.get("role") if isinstance(seed_policy, dict) else None
    kind = seed_policy.get("kind") if isinstance(seed_policy, dict) else None
    requires_binding = bool(
        (kind == "csdiy_course_cohort" and role == "examiner")
        or (
            kind == "csdiy_course_kickoff_revision"
            and role == "examiner_revision"
        )
        or (
            kind == "csdiy_course_progression"
            and role in {"examiner", "examiner_revision"}
        )
    )
    raw = payload.get("student_submission_binding")
    if raw is None:
        if requires_binding:
            raise ValueError("CSDIY examiner lacks a student submission binding")
        return None
    from .course_submission import parse_student_submission_binding

    contract = parse_student_submission_binding(raw)
    if (
        contract.student_job_id != policy.student_job_id
        or contract.student_artifact_type != policy.student_artifact_type
    ):
        raise ValueError(
            "student submission binding conflicts with learner evidence policy"
        )
    return contract


def _authoritative_submission_binding(
    connection: sqlite3.Connection,
    *,
    examiner_job_id: str,
    examiner_attempt: int,
    contract: object,
    student: sqlite3.Row | dict[str, Any],
) -> dict[str, Any] | None:
    """Resolve the one validated, immutable submission binding or fail closed."""

    from .course_submission import (
        SUBMISSION_BINDING_VALIDATOR,
        SUBMISSION_INPUT_INTEGRITY_VALIDATOR,
    )

    binding_rows = list(
        connection.execute(
            """
            SELECT evidence_json FROM validations
            WHERE job_id=? AND attempt_number=? AND validator=? AND status='PASS'
            ORDER BY validation_id
            """,
            (examiner_job_id, examiner_attempt, SUBMISSION_BINDING_VALIDATOR),
        )
    )
    integrity_rows = list(
        connection.execute(
            """
            SELECT evidence_json FROM validations
            WHERE job_id=? AND attempt_number=? AND validator=? AND status='PASS'
            ORDER BY validation_id
            """,
            (
                examiner_job_id,
                examiner_attempt,
                SUBMISSION_INPUT_INTEGRITY_VALIDATOR,
            ),
        )
    )
    if len(binding_rows) != 1 or len(integrity_rows) != 1:
        return None
    try:
        evidence = json.loads(str(binding_rows[0]["evidence_json"]))
        integrity = json.loads(str(integrity_rows[0]["evidence_json"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(evidence, dict) or not isinstance(integrity, dict):
        return None
    expected_fields = {
        "schema_version",
        "separation_policy",
        "visibility",
        "student_job_id",
        "artifact_id",
        "artifact_type",
        "artifact_attempt",
        "artifact_checksum_algorithm",
        "artifact_checksum",
        "staged_path",
        "staged_checksum_algorithm",
        "staged_checksum",
        "projection",
        "input_integrity_validator",
        "binding_sha256",
    }
    if set(evidence) != expected_fields:
        return None
    digest = evidence.get("binding_sha256")
    unsigned = dict(evidence)
    unsigned.pop("binding_sha256", None)
    projection = evidence.get("projection")
    checked = integrity.get("checked")

    def is_sha256(value: object) -> bool:
        return bool(
            isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )

    try:
        student_job_id = contract.student_job_id  # type: ignore[attr-defined]
        student_artifact_type = contract.student_artifact_type  # type: ignore[attr-defined]
        destination = contract.destination  # type: ignore[attr-defined]
    except AttributeError:
        return None
    student_keys = set(student.keys())
    artifact_attempt = (
        student["artifact_attempt"]
        if "artifact_attempt" in student_keys
        else student["student_attempt"]
    )
    if (
        evidence.get("student_job_id") != student_job_id
        or evidence.get("artifact_id") != student["artifact_id"]
        or evidence.get("artifact_type") != student_artifact_type
        or evidence.get("artifact_type") != student["artifact_type"]
        or evidence.get("artifact_attempt") != artifact_attempt
        or evidence.get("artifact_checksum_algorithm")
        != student["artifact_checksum_algorithm"]
        or evidence.get("artifact_checksum") != student["artifact_checksum"]
        or evidence.get("staged_path") != destination
        or evidence.get("staged_checksum_algorithm") != "tree-sha256-v2"
        or not is_sha256(evidence.get("staged_checksum"))
        or not isinstance(projection, dict)
        or projection.get("projected_checksum_algorithm") != "tree-sha256-v2"
        or not is_sha256(projection.get("projected_checksum"))
        or projection.get("projected_checksum")
        != evidence.get("staged_checksum")
        or not is_sha256(projection.get("paths_manifest_sha256"))
        or evidence.get("input_integrity_validator")
        != SUBMISSION_INPUT_INTEGRITY_VALIDATOR
        or not isinstance(digest, str)
        or hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()
        != digest
        or not isinstance(checked, list)
        or destination not in checked
        or integrity.get("mismatches") != []
    ):
        return None
    return evidence


_LEGACY_CSDIY_POLICY_ROLES = {
    ("csdiy_course_cohort", "examiner"),
    ("csdiy_course_kickoff_revision", "examiner_revision"),
    ("csdiy_course_progression", "examiner"),
    ("csdiy_course_progression", "examiner_revision"),
}
_LEGACY_CSDIY_INVALIDATION_REASON = (
    "legacy CSDIY examiner did not validate a checksum-bound complete student tree"
)
_LEGACY_CSDIY_REPLACEMENT_POLICY = "csdiy-examiner-submission-v1"


def _legacy_csdiy_invalidation_plan(
    connection: sqlite3.Connection,
) -> list[_LegacyAttemptInvalidationTarget]:
    """Discover missing append-only invalidations without taking a write lock."""

    legacy: dict[str, _LearnerEvidencePolicy] = {}
    for row in connection.execute(
        "SELECT job_id,payload_json FROM jobs WHERE worker_type='examiner'"
    ):
        try:
            payload = json.loads(str(row["payload_json"]))
            if not isinstance(payload, dict):
                continue
            seed_policy = payload.get("seed_policy")
            if not isinstance(seed_policy, dict) or (
                seed_policy.get("kind"), seed_policy.get("role")
            ) not in _LEGACY_CSDIY_POLICY_ROLES:
                continue
            raw_binding = payload.get("student_submission_binding")
            if raw_binding is not None:
                from .course_submission import parse_student_submission_binding

                try:
                    parse_student_submission_binding(raw_binding)
                except ValueError:
                    pass
                else:
                    continue
            policy = _parse_learner_evidence_policy(payload.get("learner_evidence"))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        legacy[str(row["job_id"])] = policy
    if not legacy:
        return []

    plan: list[_LegacyAttemptInvalidationTarget] = []
    evaluation_rows = connection.execute(
        """
        SELECT evaluation.evaluator,evaluation.result,evaluation.score,
               evaluation.evidence_json,attempt.*
        FROM evaluations evaluation
        JOIN attempts attempt ON attempt.attempt_id=evaluation.attempt_id
        ORDER BY evaluation.created_at,evaluation.evaluation_id
        """
    ).fetchall()
    for row in evaluation_rows:
        try:
            evidence = json.loads(str(row["evidence_json"]))
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(evidence, dict):
            continue
        examiner_job_id = str(evidence.get("examiner_job_id"))
        policy = legacy.get(examiner_job_id)
        if policy is None or (
            row["student_id"] != policy.student_id
            or row["task_id"] != policy.task_id
            or row["task_type"] != policy.task_type
            or row["attempt_number"] != policy.attempt_number
            or row["evaluator"] != policy.evaluator
        ):
            continue
        attempt_id = str(row["attempt_id"])
        missing_attempt = (
            connection.execute(
                "SELECT 1 FROM learner_attempt_invalidations WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            is None
        )

        evidence_targets: list[_LegacyEvidenceInvalidationTarget] = []
        observations = evidence.get("observations")
        score = row["score"]
        result = row["result"]
        if (
            isinstance(observations, list)
            and all(isinstance(item, str) for item in observations)
            and not isinstance(score, bool)
            and isinstance(score, (int, float))
            and math.isfinite(float(score))
            and result in {"PASS", "REVISE", "FAIL"}
        ):
            description_suffix = (
                f" Independent examiner result {result} with score "
                f"{float(score):g}. Observations: " + " | ".join(observations)
            )
            for concept_policy in policy.concepts:
                description = concept_policy.description + description_suffix
                evidence_id = _stable_evidence_id(
                    "evidence",
                    attempt_id,
                    concept_policy.concept,
                    concept_policy.kind,
                    description,
                )
                stored = connection.execute(
                    """
                    SELECT student_id,concept,kind,description,source_reference
                    FROM knowledge_evidence WHERE evidence_id=?
                    """,
                    (evidence_id,),
                ).fetchone()
                if (
                    stored is None
                    or stored["student_id"] != policy.student_id
                    or stored["concept"] != concept_policy.concept
                    or stored["kind"] != concept_policy.kind
                    or stored["description"] != description
                    or stored["source_reference"] != concept_policy.source_reference
                    or connection.execute(
                        """
                        SELECT 1 FROM learner_evidence_invalidations
                        WHERE evidence_id=?
                        """,
                        (evidence_id,),
                    ).fetchone()
                    is not None
                ):
                    continue
                evidence_targets.append(
                    _LegacyEvidenceInvalidationTarget(
                        evidence_id=evidence_id,
                        invalidation_id=_stable_evidence_id(
                            "evidence-invalidation", evidence_id, examiner_job_id
                        ),
                    )
                )
        if missing_attempt or evidence_targets:
            plan.append(
                _LegacyAttemptInvalidationTarget(
                    attempt_id=attempt_id,
                    examiner_job_id=examiner_job_id,
                    student_id=policy.student_id,
                    task_id=policy.task_id,
                    invalidate_attempt=missing_attempt,
                    evidence=tuple(evidence_targets),
                )
            )
    return plan


def invalidate_legacy_csdiy_learner_evidence(db: Database) -> dict[str, int]:
    """Append invalidations for narrative-only examiner evidence.

    Attempts, evaluations, and knowledge evidence are immutable historical
    records. Invalidation rows merely remove their authority from the effective
    learner model and point operators at the replacement policy. The common
    steady-state path is read-only; a short write transaction is opened only
    when the read pass identifies missing invalidations, then rechecks them.
    """

    with db.connect() as connection:
        if not _legacy_csdiy_invalidation_plan(connection):
            return {"attempts": 0, "evidence": 0}

    invalidated_attempts = 0
    invalidated_evidence = 0
    with db.transaction(immediate=True) as connection:
        for target in _legacy_csdiy_invalidation_plan(connection):
            inserted_attempt = 0
            if target.invalidate_attempt:
                inserted_attempt = connection.execute(
                    """
                    INSERT OR IGNORE INTO learner_attempt_invalidations(
                        invalidation_id,attempt_id,source_job_id,reason,
                        replacement_policy,invalidated_at
                    ) VALUES (?,?,?,?,?,?)
                    """,
                    (
                        _stable_evidence_id(
                            "attempt-invalidation",
                            target.attempt_id,
                            target.examiner_job_id,
                        ),
                        target.attempt_id,
                        target.examiner_job_id,
                        _LEGACY_CSDIY_INVALIDATION_REASON,
                        _LEGACY_CSDIY_REPLACEMENT_POLICY,
                        now(),
                    ),
                ).rowcount
            if inserted_attempt:
                invalidated_attempts += 1
                db.emit_event(
                    "learner-model",
                    "LEARNER_ATTEMPT_INVALIDATED",
                    job_id=target.examiner_job_id,
                    payload={
                        "attempt_id": target.attempt_id,
                        "student_id": target.student_id,
                        "task_id": target.task_id,
                        "reason": _LEGACY_CSDIY_INVALIDATION_REASON,
                        "replacement_policy": _LEGACY_CSDIY_REPLACEMENT_POLICY,
                        "history_preserved": True,
                    },
                    connection=connection,
                )
            for evidence_target in target.evidence:
                invalidated_evidence += connection.execute(
                    """
                    INSERT OR IGNORE INTO learner_evidence_invalidations(
                        invalidation_id,evidence_id,attempt_id,source_job_id,
                        reason,invalidated_at
                    ) VALUES (?,?,?,?,?,?)
                    """,
                    (
                        evidence_target.invalidation_id,
                        evidence_target.evidence_id,
                        target.attempt_id,
                        target.examiner_job_id,
                        _LEGACY_CSDIY_INVALIDATION_REASON,
                        now(),
                    ),
                ).rowcount
    return {"attempts": invalidated_attempts, "evidence": invalidated_evidence}


def _effective_evidence_rows(
    connection: sqlite3.Connection, student_id: str, concept: str
) -> list[sqlite3.Row]:
    return list(
        connection.execute(
            """
            SELECT evidence.evidence_id,evidence.kind,evidence.description,
                   evidence.source_reference,evidence.weight,evidence.created_at
            FROM knowledge_evidence evidence
            LEFT JOIN learner_evidence_invalidations invalidation
              ON invalidation.evidence_id=evidence.evidence_id
            WHERE evidence.student_id=? AND evidence.concept=?
              AND invalidation.evidence_id IS NULL
            ORDER BY evidence.created_at,evidence.evidence_id
            """,
            (student_id, concept),
        )
    )


def effective_learner_concepts(
    connection: sqlite3.Connection, student_id: str
) -> list[dict[str, Any]]:
    """Return learner concepts derived only from non-invalidated evidence."""

    concepts: list[dict[str, Any]] = []
    for row in connection.execute(
        """
        SELECT concept,confidence,misconceptions_json,last_updated
        FROM learner_knowledge WHERE student_id=? ORDER BY concept
        """,
        (student_id,),
    ):
        evidence = _effective_evidence_rows(
            connection, student_id, str(row["concept"])
        )
        invalidated_count = int(
            connection.execute(
                """
                SELECT COUNT(*) AS n
                FROM knowledge_evidence evidence
                JOIN learner_evidence_invalidations invalidation
                  ON invalidation.evidence_id=evidence.evidence_id
                WHERE evidence.student_id=? AND evidence.concept=?
                """,
                (student_id, row["concept"]),
            ).fetchone()["n"]
        )
        if invalidated_count and not evidence:
            continue
        confidence = float(row["confidence"])
        if evidence:
            confidence = 0.5
            for item in evidence:
                confidence = _updated_confidence(confidence, float(item["weight"]))
        concepts.append(
            {
                "concept": str(row["concept"]),
                "confidence": confidence,
                "misconceptions": (
                    []
                    if invalidated_count
                    else json.loads(str(row["misconceptions_json"]))
                ),
                "last_updated": (
                    float(evidence[-1]["created_at"])
                    if evidence
                    else float(row["last_updated"])
                ),
                "evidence": [dict(item) for item in evidence],
                "invalidated_evidence_count": invalidated_count,
            }
        )
    return concepts


def _effective_confidence_for_concept(
    connection: sqlite3.Connection,
    student_id: str,
    concept: str,
    *,
    fallback: float,
) -> float:
    evidence = _effective_evidence_rows(connection, student_id, concept)
    if evidence:
        confidence = 0.5
        for item in evidence:
            confidence = _updated_confidence(confidence, float(item["weight"]))
        return confidence
    invalidated = connection.execute(
        """
        SELECT 1 FROM knowledge_evidence evidence
        JOIN learner_evidence_invalidations invalidation
          ON invalidation.evidence_id=evidence.evidence_id
        WHERE evidence.student_id=? AND evidence.concept=? LIMIT 1
        """,
        (student_id, concept),
    ).fetchone()
    return 0.5 if invalidated is not None else fallback


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

    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        raise ValueError("knowledge evidence weight must be numeric")
    if not math.isfinite(float(weight)):
        raise ValueError("knowledge evidence weight must be finite")
    bounded_weight = max(-1.0, min(1.0, float(weight)))
    with db.transaction(immediate=True) as connection:
        current = connection.execute(
            "SELECT confidence FROM learner_knowledge WHERE student_id=? AND concept=?",
            (student_id, concept),
        ).fetchone()
        old = _effective_confidence_for_concept(
            connection,
            student_id,
            concept,
            fallback=float(current["confidence"]) if current else 0.5,
        )
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
            (
                new_id("evidence"), student_id, concept, kind, description,
                source_reference, bounded_weight, now(),
            ),
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
    staged_inputs: list[dict[str, Any]] | None = None,
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
    submission_contract = _submission_contract_for_examiner(payload, policy)
    submission_evidence = None
    if submission_contract is not None:
        from .course_submission import submission_binding_evidence

        submission_evidence = submission_binding_evidence(
            payload["student_submission_binding"], staged_inputs or []
        )
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
        if submission_contract is not None:
            authoritative_submission = _authoritative_submission_binding(
                connection,
                examiner_job_id=examiner_job_id,
                examiner_attempt=examiner_attempt,
                contract=submission_contract,
                student=context,
            )
            if (
                authoritative_submission is None
                or authoritative_submission != submission_evidence
            ):
                raise ValueError(
                    "examiner submission binding lacks matching immutable validation evidence"
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
                **(
                    {"student_submission_binding": submission_evidence}
                    if submission_evidence is not None
                    else {}
                ),
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
               artifact.path AS artifact_path,
               artifact.artifact_id AS artifact_id,
               artifact.type AS artifact_type,
               artifact.attempt_number AS artifact_attempt,
               artifact.checksum AS artifact_checksum,
               artifact.checksum_algorithm AS artifact_checksum_algorithm
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
        "artifact_id": student["artifact_id"],
        "artifact_type": student["artifact_type"],
        "artifact_attempt": student["artifact_attempt"],
        "artifact_checksum": student["artifact_checksum"],
        "artifact_checksum_algorithm": student["artifact_checksum_algorithm"],
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
            old_confidence = _effective_confidence_for_concept(
                connection,
                student_id,
                concept,
                fallback=float(existing["confidence"]),
            )
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
        concepts = effective_learner_concepts(connection, student_id)
        invalidated_evidence = [
            dict(row)
            for row in connection.execute(
                """
                SELECT evidence.evidence_id,evidence.concept,evidence.kind,
                       invalidation.attempt_id,invalidation.source_job_id,
                       invalidation.reason,invalidation.invalidated_at
                FROM knowledge_evidence evidence
                JOIN learner_evidence_invalidations invalidation
                  ON invalidation.evidence_id=evidence.evidence_id
                WHERE evidence.student_id=?
                ORDER BY invalidation.invalidated_at,evidence.evidence_id
                """,
                (student_id,),
            )
        ]
        attempts = [
            dict(row)
            for row in connection.execute(
                """
                SELECT attempt.attempt_id,attempt.task_id,attempt.task_type,
                       attempt.attempt_number,attempt.start_time,attempt.end_time,
                       attempt.result,attempt.workspace,
                       CASE WHEN invalidation.attempt_id IS NULL
                            THEN 'AUTHORITATIVE' ELSE 'SUPERSEDED' END
                            AS authority_status,
                       invalidation.reason AS invalidation_reason,
                       invalidation.replacement_policy
                FROM attempts attempt
                LEFT JOIN learner_attempt_invalidations invalidation
                  ON invalidation.attempt_id=attempt.attempt_id
                WHERE attempt.student_id=?
                ORDER BY attempt.start_time,attempt.attempt_number
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
    root = warehouse / "learners" / student_id
    root.mkdir(parents=True, exist_ok=True)
    profile = json.loads(student["profile_json"])
    (root / "PROFILE.yaml").write_text(
        _profile_yaml(student_id, student["persona"], profile), encoding="utf-8"
    )
    _write_json(
        root / "KNOWLEDGE.json",
        {
            "student_id": student_id,
            "concepts": concepts,
            "invalidated_evidence": invalidated_evidence,
        },
    )
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
                f"- Authority: {attempt['authority_status']}",
                f"- Type: {attempt['task_type']}",
                f"- Artifact: `{attempt['workspace']}`",
                f"- Evaluator: {evaluation['evaluator'] if evaluation else 'not recorded'}",
                f"- Score: {evaluation['score'] if evaluation else 'not recorded'}",
                *(
                    [f"- Supersession: {attempt['invalidation_reason']}"]
                    if attempt["authority_status"] == "SUPERSEDED"
                    else []
                ),
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
