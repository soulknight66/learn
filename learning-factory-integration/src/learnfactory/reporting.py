from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any

from .db import Database
from .jobs import JobState
from .learners import unambiguous_examiner_evaluation_result
from .util import json_value, now


_JOB_STATES = tuple(state.value for state in JobState)
_BYOX_BUILD_POLICIES = {
    "byox_reference_build",
    "byox_reference_build_s2",
    "byox_reference_repair",
    "byox_reference_repair_s2",
}
_BYOX_REVIEW_POLICIES = {
    "byox_reference_review",
    "byox_reference_review_s2",
    "byox_reference_repair_review_s2",
}
_BYOX_REVIEW_VERDICT_VALIDATOR = "byox-independent-review-verdict"
_BYOX_REVIEW_ACCEPTANCE_VALIDATOR = "byox-independent-review-acceptance"
_BYOX_REVIEW_ARTIFACT_TYPE = "byox-independent-review"
_CSDIY_COHORT_POLICY = "csdiy_course_cohort"
_CSDIY_EXAMINER_ARTIFACT_TYPE = "independent-course-evaluation"


def _source_marker(value: object) -> str:
    return str(value or "").strip().casefold().replace("_", "-").replace(" ", "-")


def _source_adapter(row: sqlite3.Row) -> str:
    metadata = json_value(row["metadata_json"], {})
    if not isinstance(metadata, dict):
        return ""
    return _source_marker(metadata.get("adapter"))


def _active_catalog_ids(
    connection: sqlite3.Connection,
) -> tuple[set[str], set[str]]:
    """Return active BYOX project and CSDIY course IDs from normalized sources."""

    byox_source_ids: set[str] = set()
    csdiy_source_ids: set[str] = set()
    for row in connection.execute(
        "SELECT source_id,type,name,metadata_json FROM sources WHERE is_active=1"
    ):
        source_type = _source_marker(row["type"])
        source_name = _source_marker(row["name"])
        adapter = _source_adapter(row)
        if (
            adapter == "build-your-own-x"
            or source_type == "build-your-own-x"
            or source_name == "build-your-own-x"
        ):
            byox_source_ids.add(str(row["source_id"]))
        # Match the course cohort seeder's active-catalog boundary while preferring
        # explicit adapter metadata when it is available.
        if (
            adapter == "csdiy"
            or source_type in {"csdiy", "course-catalog"}
            or "csdiy" in source_name
        ):
            csdiy_source_ids.add(str(row["source_id"]))

    byox_ids = {
        str(row["project_id"])
        for row in connection.execute("SELECT project_id,source_id FROM build_projects")
        if str(row["source_id"]) in byox_source_ids
    }
    csdiy_ids = {
        str(row["course_id"])
        for row in connection.execute("SELECT course_id,source_id FROM courses")
        if str(row["source_id"]) in csdiy_source_ids
    }
    return byox_ids, csdiy_ids


def _payload_record_id(payload: dict[str, Any], key: str) -> str | None:
    candidate = payload.get(key)
    if isinstance(candidate, str) and candidate:
        return candidate
    policy = payload.get("seed_policy")
    if isinstance(policy, dict):
        candidate = policy.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
    if key == "project_id":
        # Early BYOX builder payloads bound identity inside their immutable
        # provenance snapshot. Keep those jobs visible during schema rollout.
        provenance = payload.get("provenance")
        if isinstance(provenance, dict):
            project = provenance.get("project")
            if isinstance(project, dict):
                candidate = project.get("project_id")
                if isinstance(candidate, str) and candidate:
                    return candidate
    return None


def _role_state_sets(roles: tuple[str, ...]) -> dict[str, dict[str, set[str]]]:
    return {
        role: {state: set() for state in _JOB_STATES}
        for role in roles
    }


def _role_ids(role_states: dict[str, set[str]]) -> set[str]:
    identifiers: set[str] = set()
    for values in role_states.values():
        identifiers.update(values)
    return identifiers


def _state_counts(role_states: dict[str, set[str]]) -> dict[str, int]:
    return {state: len(role_states[state]) for state in _JOB_STATES}


def _percentage(part: int, whole: int) -> float:
    return round(part * 100 / whole, 1) if whole else 0.0


def _linked_byox_builder_project(row: sqlite3.Row) -> tuple[str, bool] | None:
    """Validate a reviewer's builder link and return its project and specialization."""

    payload = json_value(row["payload_json"], {})
    if not isinstance(payload, dict):
        return None
    policy = payload.get("seed_policy")
    if isinstance(policy, dict) and policy.get("kind") in _BYOX_BUILD_POLICIES:
        if policy.get("role") not in (None, "builder", "reference_builder"):
            return None
        project_id = _payload_record_id(payload, "project_id")
        return (project_id, False) if project_id is not None else None
    # This is the same structural boundary used by mass seeding to recognize an
    # existing specialized implementation instead of scheduling a duplicate.
    project_id = payload.get("project_id")
    if (
        row["worker_type"] == "reference_builder"
        and isinstance(project_id, str)
        and project_id
    ):
        return project_id, True
    return None


def _current_byox_review_outcomes(
    connection: sqlite3.Connection,
) -> dict[str, str]:
    """Return provenance-bound current review outcomes safe for workflow reporting.

    A succeeded reviewer job only proves that a review artifact was generated. A
    candidate is accepted separately: its current, verified artifact must have a
    deterministic verdict record, while PASS additionally requires a distinct,
    immutable ``review_acceptance`` command specification, its captured successful
    execution, and the REVIEWED label minted only from that validation. Conflicting,
    self-asserted, or legacy evidence fails closed.
    """

    current_builder_artifacts = {
        str(row["job_id"]): {
            "artifact_id": str(row["artifact_id"]),
            "checksum": str(row["checksum"]),
            "artifact_type": str(row["type"]),
        }
        for row in connection.execute(
            """
            SELECT j.job_id,a.artifact_id,a.checksum,a.type
            FROM jobs j JOIN artifacts a
              ON a.job_id=j.job_id AND a.attempt_number=j.attempt_count
            WHERE j.state='SUCCEEDED'
              AND a.checksum_algorithm='tree-sha256-v2'
              AND a.integrity_status='VERIFIED_V2'
            """
        )
    }
    observed: dict[str, set[str]] = {}
    review_rows = list(connection.execute(
        """
        SELECT j.job_id,j.attempt_count,j.payload_json,a.metadata_json,
               v.validation_id,v.evidence_json,v.claims_json,
               label.evidence_json AS label_evidence_json
        FROM jobs j
        JOIN artifacts a
          ON a.job_id=j.job_id
         AND a.attempt_number=j.attempt_count
         AND a.type=?
         AND a.checksum_algorithm='tree-sha256-v2'
         AND a.integrity_status='VERIFIED_V2'
        JOIN validations v
          ON v.job_id=j.job_id
         AND v.attempt_number=j.attempt_count
         AND v.validator=?
         AND v.status='PASS'
        LEFT JOIN artifact_validation_labels label
          ON label.artifact_id=a.artifact_id
         AND label.label='REVIEWED'
        WHERE j.state='SUCCEEDED'
        """,
        (_BYOX_REVIEW_ARTIFACT_TYPE, _BYOX_REVIEW_VERDICT_VALIDATOR),
    ))
    for row in review_rows:
        payload = json_value(row["payload_json"], {})
        metadata = json_value(row["metadata_json"], {})
        if not isinstance(payload, dict) or not isinstance(metadata, dict):
            continue
        validators = payload.get("validators")
        if not isinstance(validators, list):
            continue
        verdict_specs = [
            item
            for item in validators
            if isinstance(item, dict)
            and item.get("type") == "review_verdict"
            and item.get("name") == _BYOX_REVIEW_VERDICT_VALIDATOR
        ]
        if len(verdict_specs) != 1:
            continue
        builder_job_id = payload.get("builder_job_id")
        current_builder = (
            current_builder_artifacts.get(builder_job_id)
            if isinstance(builder_job_id, str)
            else None
        )
        staged_inputs = metadata.get("staged_inputs")
        bound_inputs = (
            [
                item
                for item in staged_inputs
                if isinstance(item, dict)
                and item.get("origin") == "dependency-artifact"
                and item.get("job_id") == builder_job_id
            ]
            if isinstance(staged_inputs, list)
            else []
        )
        if current_builder is None or not bound_inputs or not all(
            item.get("artifact_id") == current_builder["artifact_id"]
            and item.get("artifact_checksum") == current_builder["checksum"]
            and item.get("artifact_type") == current_builder["artifact_type"]
            for item in bound_inputs
        ):
            continue
        evidence = json_value(row["evidence_json"], {})
        if not isinstance(evidence, dict):
            continue
        verdict = evidence.get("verdict")
        if not isinstance(verdict, str) or verdict not in {"PASS", "REVISE", "FAIL"}:
            continue
        # The verdict validator is advisory under the fail-closed contract. Old
        # PASS rows that directly asserted workflow acceptance are intentionally
        # not grandfathered in.
        if evidence.get("workflow_accepted") is not False:
            continue
        recommendation = evidence.get("reviewer_recommends_acceptance")
        if recommendation is not None and recommendation != (verdict == "PASS"):
            continue
        raw_claims = json_value(row["claims_json"], [])
        claims = (
            {value for value in raw_claims if isinstance(value, str)}
            if isinstance(raw_claims, list)
            else set()
        )
        if "REVIEWED" in claims:
            continue
        label_evidence = json_value(row["label_evidence_json"], None)
        if verdict == "PASS":
            acceptance_specs = [
                item
                for item in validators
                if isinstance(item, dict)
                and item.get("type") == "review_acceptance"
                and item.get("name") == _BYOX_REVIEW_ACCEPTANCE_VALIDATOR
                and item.get("mode") == "command"
            ]
            if len(acceptance_specs) != 1:
                continue
            acceptance_spec = acceptance_specs[0]
            argv = acceptance_spec.get("argv")
            expected_exit = acceptance_spec.get("expected_exit", 0)
            if (
                acceptance_spec.get("claims") != ["REVIEWED"]
                or not isinstance(argv, list)
                or not argv
                or not all(isinstance(item, str) for item in argv)
                or isinstance(expected_exit, bool)
                or not isinstance(expected_exit, int)
            ):
                continue
            acceptance_rows = list(
                connection.execute(
                    """
                    SELECT validation_id,status,command_json,exit_code,stdout_path,
                           stderr_path,evidence_json,claims_json
                    FROM validations
                    WHERE job_id=? AND attempt_number=? AND validator=?
                    """,
                    (
                        row["job_id"],
                        row["attempt_count"],
                        _BYOX_REVIEW_ACCEPTANCE_VALIDATOR,
                    ),
                )
            )
            if len(acceptance_rows) != 1:
                continue
            acceptance = acceptance_rows[0]
            acceptance_command = json_value(acceptance["command_json"], None)
            acceptance_evidence = json_value(acceptance["evidence_json"], {})
            acceptance_claims = json_value(acceptance["claims_json"], [])
            if (
                acceptance["status"] != "PASS"
                or acceptance_command != argv
                or acceptance["exit_code"] != expected_exit
                or not acceptance["stdout_path"]
                or not acceptance["stderr_path"]
                or acceptance_claims != ["REVIEWED"]
                or not isinstance(acceptance_evidence, dict)
                or acceptance_evidence.get("mode") != "command"
                or acceptance_evidence.get("acceptance_authority")
                != "orchestrator-captured-command"
                or acceptance_evidence.get("acceptance_check_status") != "PASS"
                or acceptance_evidence.get("command_executed") is not True
                or acceptance_evidence.get("workflow_accepted") is not True
                or acceptance["validation_id"] == row["validation_id"]
            ):
                continue
            if not isinstance(label_evidence, dict):
                continue
            support = label_evidence.get("support")
            reviewed_support = (
                [
                    item
                    for item in support
                    if isinstance(item, dict)
                    and isinstance(item.get("claims"), list)
                    and "REVIEWED" in item["claims"]
                ]
                if isinstance(support, list)
                else []
            )
            if reviewed_support != [
                {
                    "validation_id": acceptance["validation_id"],
                    "validator": _BYOX_REVIEW_ACCEPTANCE_VALIDATOR,
                    "claims": ["REVIEWED"],
                }
            ]:
                continue
        elif label_evidence is not None:
            # A negative verdict carrying REVIEWED is contradictory and cannot be
            # used even as an unambiguous negative workflow outcome.
            continue
        observed.setdefault(str(row["job_id"]), set()).add(str(verdict))
    return {
        job_id: next(iter(verdicts))
        for job_id, verdicts in observed.items()
        if len(verdicts) == 1
    }


def _current_csdiy_examiner_outcomes(
    connection: sqlite3.Connection,
) -> dict[str, str]:
    """Return unambiguous, current-attempt course examiner outcomes.

    A terminal Codex process and an archived directory are workflow evidence, not
    proof that the learner passed.  Accept only a current VERIFIED_V2 examiner
    artifact plus a control-plane-published evaluation bound to the examiner's
    exact job attempt and declared learner/task attempt.
    """

    observed: dict[str, set[str]] = {}
    for row in connection.execute(
        """
        SELECT DISTINCT j.job_id,j.attempt_count,j.payload_json
        FROM jobs j JOIN artifacts artifact
          ON artifact.job_id=j.job_id
         AND artifact.attempt_number=j.attempt_count
         AND artifact.type=?
         AND artifact.checksum_algorithm='tree-sha256-v2'
         AND artifact.integrity_status='VERIFIED_V2'
        WHERE j.state='SUCCEEDED'
        """,
        (_CSDIY_EXAMINER_ARTIFACT_TYPE,),
    ):
        payload = json_value(row["payload_json"], {})
        if not isinstance(payload, dict):
            continue
        policy = payload.get("learner_evidence")
        if not isinstance(policy, dict):
            continue
        if policy.get("schema_version") == 1:
            outcome = unambiguous_examiner_evaluation_result(
                connection, str(row["job_id"])
            )
            if outcome is not None:
                observed.setdefault(str(row["job_id"]), set()).add(outcome)
            # Current versioned evidence is never downgraded to the permissive
            # compatibility reader below. A malformed or contradictory bundle
            # remains unknown/invalid instead of becoming a PASS claim.
            continue
        student_id = policy.get("student_id")
        task_id = policy.get("task_id")
        learner_attempt = policy.get("attempt_number")
        if (
            not isinstance(student_id, str)
            or not student_id
            or not isinstance(task_id, str)
            or not task_id
            or isinstance(learner_attempt, bool)
            or not isinstance(learner_attempt, int)
        ):
            continue
        for evaluation in connection.execute(
            """
            SELECT evaluation.result,evaluation.evidence_json
            FROM attempts attempt JOIN evaluations evaluation
              ON evaluation.attempt_id=attempt.attempt_id
            WHERE attempt.student_id=? AND attempt.task_id=?
              AND attempt.attempt_number=?
              AND evaluation.result IN ('PASS','REVISE','FAIL')
            """,
            (student_id, task_id, learner_attempt),
        ):
            evidence = json_value(evaluation["evidence_json"], {})
            if not isinstance(evidence, dict):
                continue
            if (
                evidence.get("examiner_job_id") == row["job_id"]
                and evidence.get("examiner_attempt") == row["attempt_count"]
            ):
                observed.setdefault(str(row["job_id"]), set()).add(
                    str(evaluation["result"])
                )
    return {
        job_id: next(iter(outcomes))
        for job_id, outcomes in observed.items()
        if len(outcomes) == 1
    }


def _scaleout_coverage(connection: sqlite3.Connection) -> dict[str, Any]:
    """Summarize catalog graph coverage solely from versioned seed-policy metadata."""

    byox_catalog, csdiy_catalog = _active_catalog_ids(connection)
    byox_states = _role_state_sets(("builder", "reviewer"))
    csdiy_states = _role_state_sets(("manager", "student", "examiner"))
    byox_orphans: set[str] = set()
    csdiy_orphans: set[str] = set()
    specialized_builders: set[str] = set()
    review_job_succeeded_pairs: set[str] = set()
    review_outcomes_by_project: dict[str, dict[int, set[str]]] = {}
    seeded_review_versions_by_project: dict[str, set[int]] = {}
    byox_unattributed = 0
    csdiy_unattributed = 0
    current_review_outcomes = _current_byox_review_outcomes(connection)
    current_csdiy_examiner_outcomes = _current_csdiy_examiner_outcomes(connection)
    csdiy_examiner_outcomes_by_course: dict[str, set[str]] = {}
    csdiy_cohort_job_candidates: dict[str, dict[str, set[str]]] = {}
    verified_current_artifact_jobs = {
        str(row["job_id"])
        for row in connection.execute(
            """
            SELECT j.job_id
            FROM jobs j JOIN artifacts a
              ON a.job_id=j.job_id AND a.attempt_number=j.attempt_count
            WHERE j.state='SUCCEEDED'
              AND a.checksum_algorithm='tree-sha256-v2'
              AND a.integrity_status='VERIFIED_V2'
            """
        )
    }

    job_rows = list(
        connection.execute("SELECT job_id,worker_type,state,payload_json FROM jobs")
    )
    jobs_by_id = {str(row["job_id"]): row for row in job_rows}
    for row in job_rows:
        payload = json_value(row["payload_json"], {})
        if not isinstance(payload, dict):
            continue
        policy = payload.get("seed_policy")
        if not isinstance(policy, dict):
            continue
        kind = policy.get("kind")
        role = policy.get("role")
        state = str(row["state"])
        if state not in _JOB_STATES:
            continue

        byox_role: str | None = None
        if kind in _BYOX_BUILD_POLICIES and role in (None, "builder", "reference_builder"):
            byox_role = "builder"
        elif kind in _BYOX_REVIEW_POLICIES and role in (None, "reviewer", "examiner"):
            byox_role = "reviewer"
        # Tolerate a short-lived draft shape that put both roles under the build
        # policy kind; canonical new jobs use the separate review kind above.
        elif kind in _BYOX_BUILD_POLICIES and role in ("reviewer", "examiner"):
            byox_role = "reviewer"
        if byox_role is not None:
            project_id = _payload_record_id(payload, "project_id")
            if project_id is None:
                byox_unattributed += 1
            elif project_id in byox_catalog:
                byox_states[byox_role][state].add(project_id)
                if byox_role == "reviewer":
                    raw_version = policy.get("version", 0)
                    policy_version = (
                        raw_version
                        if isinstance(raw_version, int)
                        and not isinstance(raw_version, bool)
                        and raw_version >= 0
                        else 0
                    )
                    seeded_review_versions_by_project.setdefault(
                        project_id, set()
                    ).add(policy_version)
                    builder_job_id = payload.get("builder_job_id")
                    builder_row = (
                        jobs_by_id.get(builder_job_id)
                        if isinstance(builder_job_id, str)
                        else None
                    )
                    if builder_row is not None:
                        linked = _linked_byox_builder_project(builder_row)
                        builder_state = str(builder_row["state"])
                        if (
                            linked is not None
                            and linked[0] == project_id
                            and builder_state in _JOB_STATES
                        ):
                            byox_states["builder"][builder_state].add(project_id)
                            if linked[1]:
                                specialized_builders.add(project_id)
                            if (
                                state == JobState.SUCCEEDED.value
                                and builder_state == JobState.SUCCEEDED.value
                                and str(builder_job_id)
                                in verified_current_artifact_jobs
                            ):
                                review_job_succeeded_pairs.add(project_id)
                                review_outcomes_by_project.setdefault(
                                    project_id, {}
                                ).setdefault(policy_version, set()).add(
                                    current_review_outcomes.get(
                                        str(row["job_id"]), "UNKNOWN"
                                    )
                                )
            else:
                byox_orphans.add(project_id)
            continue

        if kind != _CSDIY_COHORT_POLICY:
            continue
        csdiy_role = {
            "preparation": "manager",
            "manager": "manager",
            "course_manager": "manager",
            "student": "student",
            "examiner": "examiner",
        }.get(role)
        if csdiy_role is None:
            continue
        course_id = _payload_record_id(payload, "course_id")
        if course_id is None:
            csdiy_unattributed += 1
        elif course_id in csdiy_catalog:
            csdiy_states[csdiy_role][state].add(course_id)
            csdiy_cohort_job_candidates.setdefault(course_id, {}).setdefault(
                str(role), set()
            ).add(str(row["job_id"]))
            if csdiy_role == "examiner" and state == JobState.SUCCEEDED.value:
                outcome = current_csdiy_examiner_outcomes.get(str(row["job_id"]))
                if outcome is not None:
                    csdiy_examiner_outcomes_by_course.setdefault(
                        course_id, set()
                    ).add(outcome)
        else:
            csdiy_orphans.add(course_id)

    builder_ids = _role_ids(byox_states["builder"])
    reviewer_ids = _role_ids(byox_states["reviewer"])
    byox_planned = builder_ids | reviewer_ids
    complete_pairs = builder_ids & reviewer_ids
    authoritative_review_outcomes = {
        project_id: review_outcomes_by_project.get(project_id, {}).get(
            max(versions), {"UNKNOWN"}
        )
        for project_id, versions in seeded_review_versions_by_project.items()
        if versions
    }
    succeeded_pairs = {
        project_id
        for project_id, verdicts in authoritative_review_outcomes.items()
        if verdicts == {"PASS"}
    }
    review_outcome_counts = {
        verdict: sum(
            verdicts == {verdict}
            for verdicts in authoritative_review_outcomes.values()
        )
        for verdict in ("PASS", "REVISE", "FAIL", "UNKNOWN")
    }
    review_outcome_counts["AMBIGUOUS"] = sum(
        len(verdicts) != 1 for verdicts in authoritative_review_outcomes.values()
    )

    manager_ids = _role_ids(csdiy_states["manager"])
    student_ids = _role_ids(csdiy_states["student"])
    examiner_ids = _role_ids(csdiy_states["examiner"])
    csdiy_planned = manager_ids | student_ids | examiner_ids
    from .course_kickoff_revisions import authoritative_kickoff_revision_outcomes

    cohort_jobs: dict[str, dict[str, str]] = {}
    cohort_versions: dict[str, dict[str, int]] = {}
    historical_versions: dict[str, dict[str, set[int]]] = {}
    for course_id, roles in csdiy_cohort_job_candidates.items():
        selected: dict[str, str] = {}
        for role, candidates in roles.items():
            by_version: dict[int, set[str]] = {}
            for candidate in candidates:
                row = jobs_by_id.get(candidate)
                candidate_payload = (
                    json_value(row["payload_json"], {}) if row is not None else {}
                )
                candidate_policy = (
                    candidate_payload.get("seed_policy")
                    if isinstance(candidate_payload, dict)
                    else None
                )
                raw_version = (
                    candidate_policy.get("version")
                    if isinstance(candidate_policy, dict)
                    else None
                )
                version = (
                    raw_version
                    if isinstance(raw_version, int)
                    and not isinstance(raw_version, bool)
                    and raw_version >= 1
                    else 0
                )
                by_version.setdefault(version, set()).add(candidate)
            historical_versions.setdefault(course_id, {})[role] = set(by_version)
            if by_version:
                latest = by_version[max(by_version)]
                if len(latest) == 1:
                    selected[role] = next(iter(latest))
                    cohort_versions.setdefault(course_id, {})[role] = max(by_version)
        cohort_jobs[course_id] = selected
    active_contract_complete_cohorts = {
        course_id
        for course_id, selected in cohort_jobs.items()
        if set(selected) == {"preparation", "student", "examiner"}
    }
    active_contract_archived_output_cohorts = {
        course_id
        for course_id in active_contract_complete_cohorts
        if all(
            str(jobs_by_id[job_id]["state"]) == JobState.SUCCEEDED.value
            and job_id in verified_current_artifact_jobs
            for job_id in cohort_jobs[course_id].values()
        )
    }
    complete_cohorts = manager_ids & student_ids & examiner_ids
    archived_output_cohorts = (
        csdiy_states["manager"][JobState.SUCCEEDED.value]
        & csdiy_states["student"][JobState.SUCCEEDED.value]
        & csdiy_states["examiner"][JobState.SUCCEEDED.value]
    )
    remediated_cohorts = {
        course_id
        for course_id, versions in cohort_versions.items()
        if versions.get("student", 0) >= 2
        and versions.get("examiner", 0) >= 2
        and (
            1 in historical_versions.get(course_id, {}).get("student", set())
            or 1 in historical_versions.get(course_id, {}).get("examiner", set())
        )
    }
    superseded_legacy_jobs = int(
        connection.execute(
            """
            SELECT COUNT(*) AS n FROM jobs
            WHERE failure_kind='superseded_submission_contract'
            """
        ).fetchone()["n"]
    )
    (
        csdiy_examiner_outcomes_by_course,
        invalid_kickoff_revision_chains,
    ) = authoritative_kickoff_revision_outcomes(
        connection,
        cohort_jobs=cohort_jobs,
        initial_outcomes=csdiy_examiner_outcomes_by_course,
        examiner_outcomes=current_csdiy_examiner_outcomes,
        gate_job_id="job_codex_backend_gate_v1",
    )
    succeeded_cohorts = {
        course_id
        for course_id in archived_output_cohorts
        if csdiy_examiner_outcomes_by_course.get(course_id) == {"PASS"}
    }
    csdiy_examiner_outcome_counts = {
        verdict: sum(
            outcomes == {verdict}
            for outcomes in csdiy_examiner_outcomes_by_course.values()
        )
        for verdict in ("PASS", "REVISE", "FAIL")
    }
    csdiy_examiner_outcome_counts["UNKNOWN"] = sum(
        course_id not in csdiy_examiner_outcomes_by_course
        and course_id not in invalid_kickoff_revision_chains
        for course_id in csdiy_states["examiner"][JobState.SUCCEEDED.value]
    )
    csdiy_examiner_outcome_counts["AMBIGUOUS"] = sum(
        len(outcomes) != 1
        for outcomes in csdiy_examiner_outcomes_by_course.values()
    ) + len(invalid_kickoff_revision_chains)

    return {
        "byox": {
            "catalog_entries": len(byox_catalog),
            "planned_entries": len(byox_planned),
            "unplanned_entries": len(byox_catalog - byox_planned),
            "coverage_percent": _percentage(len(byox_planned), len(byox_catalog)),
            "builder_entries": len(builder_ids),
            "specialized_builder_entries": len(specialized_builders),
            "reviewer_entries": len(reviewer_ids),
            "complete_pairs": len(complete_pairs),
            "complete_pair_percent": _percentage(len(complete_pairs), len(byox_catalog)),
            "review_job_succeeded_pairs": len(review_job_succeeded_pairs),
            "succeeded_pairs": len(succeeded_pairs),
            "review_outcomes": review_outcome_counts,
            "builder_states": _state_counts(byox_states["builder"]),
            "reviewer_states": _state_counts(byox_states["reviewer"]),
            "orphaned_entries": len(byox_orphans),
            "unattributed_jobs": byox_unattributed,
        },
        "csdiy": {
            "catalog_entries": len(csdiy_catalog),
            "planned_entries": len(csdiy_planned),
            "unplanned_entries": len(csdiy_catalog - csdiy_planned),
            "coverage_percent": _percentage(len(csdiy_planned), len(csdiy_catalog)),
            "manager_entries": len(manager_ids),
            "student_entries": len(student_ids),
            "examiner_entries": len(examiner_ids),
            "complete_cohorts": len(complete_cohorts),
            "complete_cohort_percent": _percentage(
                len(complete_cohorts), len(csdiy_catalog)
            ),
            "archived_output_cohorts": len(archived_output_cohorts),
            "active_contract_complete_cohorts": len(
                active_contract_complete_cohorts
            ),
            "active_contract_archived_output_cohorts": len(
                active_contract_archived_output_cohorts
            ),
            "succeeded_cohorts": len(succeeded_cohorts),
            "remediated_cohorts": len(remediated_cohorts),
            "superseded_legacy_jobs": superseded_legacy_jobs,
            "active_cohort_contract": (
                "v1 preparation + v2 checksum-bound student/examiner"
            ),
            "invalid_kickoff_revision_chains": len(
                invalid_kickoff_revision_chains
            ),
            "examiner_outcomes": csdiy_examiner_outcome_counts,
            "manager_states": _state_counts(csdiy_states["manager"]),
            "student_states": _state_counts(csdiy_states["student"]),
            "examiner_states": _state_counts(csdiy_states["examiner"]),
            "orphaned_entries": len(csdiy_orphans),
            "unattributed_jobs": csdiy_unattributed,
        },
    }


def status_snapshot(db: Database) -> dict[str, Any]:
    with db.read_transaction() as connection:
        paused_row = connection.execute(
            "SELECT value_json FROM system_state WHERE key='paused'"
        ).fetchone()
        paused = (
            bool(json_value(paused_row["value_json"], False))
            if paused_row is not None
            else False
        )
        job_states = {
            row["state"]: row["n"]
            for row in connection.execute("SELECT state,COUNT(*) AS n FROM jobs GROUP BY state")
        }
        workers = [
            dict(row)
            for row in connection.execute(
                """
                SELECT w.worker_id,w.type,w.process_id,w.state,w.current_job,
                       w.started_at,w.last_activity,w.workspace,w.error,
                       r.backend,r.model,r.reasoning_effort,r.session_id,
                       r.provider,r.base_url,r.wire_api,r.supports_websockets
                FROM workers w
                LEFT JOIN job_runs r ON r.worker_id=w.worker_id
                                     AND r.finished_at IS NULL
                WHERE w.state IN ('STARTING','RUNNING') ORDER BY w.started_at
                """
            )
        ]
        counts = {
            "sources": connection.execute(
                "SELECT COUNT(*) AS n FROM sources WHERE is_active=1"
            ).fetchone()["n"],
            "courses": connection.execute(
                """
                SELECT COUNT(*) AS n FROM courses c
                JOIN sources s ON s.source_id=c.source_id WHERE s.is_active=1
                """
            ).fetchone()["n"],
            "course_units": connection.execute(
                """
                SELECT COUNT(*) AS n FROM course_units u
                JOIN courses c ON c.course_id=u.course_id
                JOIN sources s ON s.source_id=c.source_id WHERE s.is_active=1
                """
            ).fetchone()["n"],
            "projects": connection.execute(
                """
                SELECT COUNT(*) AS n FROM build_projects p
                JOIN sources s ON s.source_id=p.source_id WHERE s.is_active=1
                """
            ).fetchone()["n"],
            "students": connection.execute("SELECT COUNT(*) AS n FROM students").fetchone()["n"],
            "artifacts": connection.execute(
                """
                SELECT COUNT(*) AS n FROM artifacts a JOIN jobs j ON j.job_id=a.job_id
                WHERE j.state='SUCCEEDED' AND a.attempt_number=j.attempt_count
                """
            ).fetchone()["n"],
            "validations": connection.execute("SELECT COUNT(*) AS n FROM validations").fetchone()["n"],
            "events": connection.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"],
        }
        failures = [
            dict(row)
            for row in connection.execute(
                """
                SELECT job_id,type,worker_type,attempt_count,max_attempts,
                       retry_allowance,
                       max_attempts+retry_allowance AS effective_attempt_limit,
                       failure_kind,error,finished_at
                FROM jobs WHERE state='FAILED' ORDER BY finished_at DESC LIMIT 10
                """
            )
        ]
        problems = [
            dict(row)
            for row in connection.execute(
                """
                SELECT job_id,type,worker_type,state,attempt_count,max_attempts,
                       retry_allowance,
                       max_attempts+retry_allowance AS effective_attempt_limit,
                       failure_kind,error,COALESCE(finished_at,heartbeat_at,created_at) AS occurred_at
                FROM jobs WHERE state IN ('FAILED','BLOCKED')
                ORDER BY occurred_at DESC LIMIT 10
                """
            )
        ]
        next_ready = [
            dict(row)
            for row in connection.execute(
                """
                SELECT job_id,type,worker_type,priority,attempt_count,max_attempts,
                       retry_allowance,
                       max_attempts+retry_allowance AS effective_attempt_limit
                FROM jobs WHERE state='READY' ORDER BY priority DESC,created_at,job_id LIMIT 10
                """
            )
        ]
        completed_by_type = {
            row["type"]: row["n"]
            for row in connection.execute(
                "SELECT type,COUNT(*) AS n FROM jobs WHERE state='SUCCEEDED' GROUP BY type"
            )
        }
        durations = [
            float(row["duration"])
            for row in connection.execute(
                """
                SELECT finished_at-started_at AS duration FROM jobs
                WHERE finished_at IS NOT NULL AND started_at IS NOT NULL
                  AND finished_at >= started_at ORDER BY duration
                """
            )
        ]
        retry_count = connection.execute(
            "SELECT COALESCE(SUM(CASE WHEN attempt_count>0 THEN attempt_count-1 ELSE 0 END),0) AS n FROM jobs"
        ).fetchone()["n"]
        labels = {
            row["label"]: row["n"]
            for row in connection.execute(
                "SELECT label,COUNT(*) AS n FROM artifact_validation_labels GROUP BY label"
            )
        }
        course_status = {
            row["status"]: row["n"]
            for row in connection.execute(
                """
                SELECT c.status,COUNT(*) AS n FROM courses c
                JOIN sources s ON s.source_id=c.source_id
                WHERE s.is_active=1 GROUP BY c.status
                """
            )
        }
        project_tiers = {
            str(row["priority_tier"]): row["n"]
            for row in connection.execute(
                """
                SELECT p.priority_tier,COUNT(*) AS n FROM build_projects p
                JOIN sources s ON s.source_id=p.source_id
                WHERE s.is_active=1 GROUP BY p.priority_tier
                """
            )
        }
        scaleout_coverage = _scaleout_coverage(connection)
    median_duration = None
    if durations:
        middle = len(durations) // 2
        median_duration = (
            durations[middle]
            if len(durations) % 2
            else (durations[middle - 1] + durations[middle]) / 2
        )
    return {
        "generated_at": now(),
        "paused": paused,
        "jobs": job_states,
        "counts": counts,
        "active_workers": workers,
        "recent_failures": failures,
        "recent_problems": problems,
        "next_ready": next_ready,
        "metrics": {
            "retry_count": retry_count,
            "median_finished_job_duration_seconds": median_duration,
            "completed_by_type": completed_by_type,
            "artifact_labels": labels,
            "course_status": course_status,
            "project_priority_tiers": project_tiers,
            "scaleout_coverage": scaleout_coverage,
        },
    }


def write_checkpoint(db: Database, reports: Path, warehouse: Path) -> tuple[Path, Path]:
    snapshot = status_snapshot(db)
    reports.mkdir(parents=True, exist_ok=True)
    json_path = reports / "latest.json"
    markdown_path = reports / "latest.md"
    json_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    timestamp = dt.datetime.fromtimestamp(snapshot["generated_at"], dt.timezone.utc).isoformat()
    lines = [
        "# Learning Factory checkpoint",
        "",
        f"Generated: {timestamp}",
        f"Paused: {snapshot['paused']}",
        "",
        "## Health",
        "",
        "| Job state | Count |",
        "|---|---:|",
    ]
    for state, count in sorted(snapshot["jobs"].items()):
        lines.append(f"| {state} | {count} |")
    lines.extend(["", "## Corpus", "", "| Item | Count |", "|---|---:|"])
    for name, count in snapshot["counts"].items():
        lines.append(f"| {name} | {count} |")
    scaleout = snapshot["metrics"]["scaleout_coverage"]
    byox = scaleout["byox"]
    csdiy = scaleout["csdiy"]
    byox_builder_states = {
        state: count for state, count in byox["builder_states"].items() if count
    }
    byox_reviewer_states = {
        state: count for state, count in byox["reviewer_states"].items() if count
    }
    csdiy_role_states = {
        role: {state: count for state, count in csdiy[f"{role}_states"].items() if count}
        for role in ("manager", "student", "examiner")
    }
    lines.extend(
        [
            "",
            "## Scale-out coverage",
            "",
            (
                f"- BYOX: {byox['planned_entries']}/{byox['catalog_entries']} entries planned; "
                f"builders {byox['builder_entries']}, reviewers {byox['reviewer_entries']}, "
                f"graph-complete pairs {byox['complete_pairs']}, review outputs succeeded "
                f"{byox['review_job_succeeded_pairs']}, verdict-accepted pairs "
                f"{byox['succeeded_pairs']}, review outcomes "
                f"`{json.dumps(byox['review_outcomes'], sort_keys=True)}`, specialized builders "
                f"{byox['specialized_builder_entries']}; states "
                f"`builder={json.dumps(byox_builder_states, sort_keys=True)}` "
                f"`reviewer={json.dumps(byox_reviewer_states, sort_keys=True)}`."
            ),
            (
                f"- CSDIY: {csdiy['planned_entries']}/{csdiy['catalog_entries']} courses planned; "
                f"managers {csdiy['manager_entries']}, students {csdiy['student_entries']}, "
                f"examiners {csdiy['examiner_entries']}, graph-complete cohorts "
                f"{csdiy['complete_cohorts']}, workflow-succeeded cohorts "
                f"{csdiy['succeeded_cohorts']}, archived-output cohorts "
                f"{csdiy['archived_output_cohorts']}, remediated cohorts "
                f"{csdiy['remediated_cohorts']}, superseded legacy jobs "
                f"{csdiy['superseded_legacy_jobs']}, active-contract complete/archive "
                f"{csdiy['active_contract_complete_cohorts']}/"
                f"{csdiy['active_contract_archived_output_cohorts']}, examiner outcomes "
                f"`{json.dumps(csdiy['examiner_outcomes'], sort_keys=True)}`, invalid kickoff "
                f"revision chains {csdiy['invalid_kickoff_revision_chains']}; states "
                f"`{json.dumps(csdiy_role_states, sort_keys=True)}`."
            ),
        ]
    )
    lines.extend(["", "## Active workers", ""])
    if snapshot["active_workers"]:
        for worker in snapshot["active_workers"]:
            lines.append(
                f"- `{worker['worker_id']}`: {worker['type']} / {worker['current_job']} "
                f"(backend={worker.get('backend')}, model={worker.get('model')}, "
                f"reasoning={worker.get('reasoning_effort')}, "
                f"provider={worker.get('provider')}, session={worker.get('session_id')})"
            )
    else:
        lines.append("None.")
    lines.extend(["", "## Problems requiring attention", ""])
    if snapshot["recent_problems"]:
        for failure in snapshot["recent_problems"]:
            lines.append(
                f"- `{failure['job_id']}` [{failure['state']}] "
                f"({failure['failure_kind']}): {failure['error']}"
            )
    else:
        lines.append("None.")
    lines.extend(["", "## Next ready work", ""])
    if snapshot["next_ready"]:
        for job in snapshot["next_ready"]:
            lines.append(
                f"- `{job['job_id']}`: {job['type']} / {job['worker_type']} "
                f"(priority {job['priority']:.1f})"
            )
    else:
        lines.append("None.")
    lines.extend(
        [
            "",
            "## Operational metrics",
            "",
            f"- Persisted retries: {snapshot['metrics']['retry_count']}",
            f"- Median finished-job duration: {snapshot['metrics']['median_finished_job_duration_seconds']}",
            f"- Completed by type: `{json.dumps(snapshot['metrics']['completed_by_type'], sort_keys=True)}`",
            f"- Artifact labels: `{json.dumps(snapshot['metrics']['artifact_labels'], sort_keys=True)}`",
        ]
    )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_catalog(db, warehouse / "catalog")
    return markdown_path, json_path


def write_catalog(db: Database, catalog_dir: Path) -> tuple[Path, Path]:
    catalog_dir.mkdir(parents=True, exist_ok=True)
    # Materialize every section from one deferred SQLite read snapshot.
    with db.transaction() as connection:
        artifacts = []
        for row in connection.execute(
            """
            SELECT a.*,j.type AS job_type,j.worker_type FROM artifacts a
            JOIN jobs j ON j.job_id=a.job_id
            WHERE j.state='SUCCEEDED' AND a.attempt_number=j.attempt_count
            ORDER BY a.created_at DESC
            """
        ):
            item = dict(row)
            item["metadata"] = json_value(item.pop("metadata_json"), {})
            item["validation_labels"] = [
                label["label"]
                for label in connection.execute(
                    "SELECT label FROM artifact_validation_labels WHERE artifact_id=? ORDER BY label",
                    (item["artifact_id"],),
                )
            ]
            artifacts.append(item)
        sources = []
        for row in connection.execute(
            "SELECT * FROM sources WHERE is_active=1 ORDER BY name,commit_hash"
        ):
            item = dict(row)
            item["metadata"] = json_value(item.pop("metadata_json"), {})
            sources.append(item)
        courses = []
        for row in connection.execute(
            """
            SELECT c.course_id,c.source_id,c.slug,c.institution,c.title,c.topic,
                   c.description,c.prerequisites_json,c.estimated_human_hours,
                   c.difficulty,c.source_metadata_json,c.status
            FROM courses c JOIN sources s ON s.source_id=c.source_id
            WHERE s.is_active=1 ORDER BY c.topic,c.title
            """
        ):
            item = dict(row)
            item["prerequisites"] = json_value(item.pop("prerequisites_json"), [])
            item["source_metadata"] = json_value(item.pop("source_metadata_json"), {})
            courses.append(item)
        projects = []
        for row in connection.execute(
            """
            SELECT p.project_id,p.source_id,p.slug,p.title,p.category,
                   p.implementation_language,p.upstream_reference,p.concepts_json,
                   p.difficulty,p.production_relevance,p.source_format,
                   p.priority_tier,p.metadata_json
            FROM build_projects p JOIN sources s ON s.source_id=p.source_id
            WHERE s.is_active=1 ORDER BY p.priority_tier,p.category,p.title
            """
        ):
            item = dict(row)
            item["concepts"] = json_value(item.pop("concepts_json"), [])
            item["metadata"] = json_value(item.pop("metadata_json"), {})
            projects.append(item)
        course_topics = [dict(row) for row in connection.execute(
            """
            SELECT c.topic,COUNT(*) AS count FROM courses c
            JOIN sources s ON s.source_id=c.source_id
            WHERE s.is_active=1 GROUP BY c.topic ORDER BY count DESC
            """
        )]
        project_categories = [dict(row) for row in connection.execute(
            """
            SELECT p.category,COUNT(*) AS count FROM build_projects p
            JOIN sources s ON s.source_id=p.source_id
            WHERE s.is_active=1 GROUP BY p.category ORDER BY count DESC
            """
        )]
    payload = {
        "generated_at": now(),
        "sources": sources,
        "courses": courses,
        "projects": projects,
        "artifacts": artifacts,
        "course_topics": course_topics,
        "project_categories": project_categories,
    }
    machine = catalog_dir / "catalog.json"
    human = catalog_dir / "README.md"
    machine.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Learning artifact catalog",
        "",
        f"Sources: {len(sources)}. Courses: {len(courses)}. Build projects: {len(projects)}. Validated artifacts: {len(artifacts)}.",
        "",
        "The complete searchable records, concepts, languages, provenance, and validation labels are in `catalog.json`.",
        "",
    ]
    for item in artifacts:
        metadata = item["metadata"]
        display_name = str(metadata.get("name") or metadata.get("title") or item["type"])
        family = metadata.get("family")
        languages = metadata.get("languages")
        concepts = metadata.get("concepts")
        lines.extend(
            [
                f"## {display_name} — {item['validation_status']}",
                "",
                f"- Artifact type: `{item['type']}`",
                f"- Path: `{item['path']}`",
                f"- SHA-256: `{item['checksum']}`",
                f"- Hash format: `{item['checksum_algorithm']}`",
                f"- Integrity: `{item['integrity_status']}`",
                f"- Labels: {', '.join(item['validation_labels'])}",
                f"- Job: `{item['job_id']}` ({item['job_type']}/{item['worker_type']})",
            ]
        )
        if family:
            lines.append(f"- Family: {family}")
        if isinstance(languages, list) and languages:
            lines.append(f"- Languages: {', '.join(str(value) for value in languages)}")
        if isinstance(concepts, list) and concepts:
            lines.append(f"- Concepts: {', '.join(str(value) for value in concepts)}")
        if metadata.get("difficulty") is not None:
            lines.append(f"- Difficulty: {metadata['difficulty']}")
        if metadata.get("estimated_human_hours") is not None:
            lines.append(f"- Estimated study time: {metadata['estimated_human_hours']} hours")
        lines.append("")
    human.write_text("\n".join(lines), encoding="utf-8")
    return human, machine
