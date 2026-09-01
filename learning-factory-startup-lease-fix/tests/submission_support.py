from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

from learnfactory.course_submission import (
    SUBMISSION_BINDING_VALIDATOR,
    SUBMISSION_INPUT_INTEGRITY_VALIDATOR,
    parse_student_submission_binding,
    submission_binding_evidence,
)
from learnfactory.util import canonical_json


def insert_submission_binding_validations(
    connection: sqlite3.Connection,
    *,
    examiner_job_id: str,
    examiner_attempt: int,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    """Insert deterministic fixture evidence for the real hardened contract."""

    raw = payload.get("student_submission_binding")
    if raw is None:
        return None
    contract = parse_student_submission_binding(raw)
    artifact = connection.execute(
        """
        SELECT a.artifact_id,a.type,a.checksum,a.checksum_algorithm,a.attempt_number
        FROM jobs j JOIN artifacts a
          ON a.job_id=j.job_id AND a.attempt_number=j.attempt_count
        WHERE j.job_id=? AND j.state='SUCCEEDED'
        """,
        (contract.student_job_id,),
    ).fetchone()
    if artifact is None:
        raise AssertionError("submission fixture requires a current student artifact")
    staged_checksum = hashlib.sha256(
        f"{examiner_job_id}\0{artifact['checksum']}".encode("utf-8")
    ).hexdigest()
    projection = {
        "schema_version": 1,
        "source_prefix": ".",
        "regular_file_count": 1,
        "total_bytes": 1,
        "code_file_count": 0,
        "test_file_count": 0,
        "code_path_samples": [],
        "test_path_samples": [],
        "excluded_paths": [],
        "excluded_path_count": 0,
        "paths_manifest_sha256": "1" * 64,
        "projected_checksum_algorithm": "tree-sha256-v2",
        "projected_checksum": staged_checksum,
        "limits": {
            "max_entries": 20_000,
            "max_files": 10_000,
            "max_total_bytes": 256 * 1024 * 1024,
            "max_file_bytes": 32 * 1024 * 1024,
            "max_depth": 80,
        },
    }
    evidence = submission_binding_evidence(
        raw,
        [
            {
                "path": contract.destination,
                "kind": "directory",
                "checksum_algorithm": "tree-sha256-v2",
                "checksum": staged_checksum,
                "origin": "dependency-artifact",
                "job_id": contract.student_job_id,
                "artifact_id": artifact["artifact_id"],
                "artifact_type": artifact["type"],
                "artifact_checksum": artifact["checksum"],
                "artifact_checksum_algorithm": artifact["checksum_algorithm"],
                "artifact_attempt": artifact["attempt_number"],
                "artifact_subpath": ".",
                "student_submission_projection": projection,
            }
        ],
    )
    suffix = hashlib.sha256(examiner_job_id.encode("utf-8")).hexdigest()[:20]
    rows = (
        (
            f"validation_submission_binding_{suffix}",
            SUBMISSION_BINDING_VALIDATOR,
            evidence,
        ),
        (
            f"validation_submission_integrity_{suffix}",
            SUBMISSION_INPUT_INTEGRITY_VALIDATOR,
            {"checked": [contract.destination], "mismatches": []},
        ),
    )
    for validation_id, validator, validation_evidence in rows:
        connection.execute(
            """
            INSERT INTO validations(
                validation_id,job_id,validator,status,command_json,exit_code,
                stdout_path,stderr_path,evidence_json,started_at,finished_at,
                attempt_number,claims_json
            ) VALUES (?,?,?,'PASS',NULL,NULL,NULL,NULL,?,?,?,?,'[]')
            """,
            (
                validation_id,
                examiner_job_id,
                validator,
                canonical_json(validation_evidence),
                100.0,
                101.0,
                examiner_attempt,
            ),
        )
    return evidence
