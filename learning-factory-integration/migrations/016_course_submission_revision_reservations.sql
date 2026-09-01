CREATE TABLE course_progression_submission_revision_reservations (
    course_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_commit_hash TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK(sequence > 0),
    batch_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK(attempt_number >= 2),
    submission_contract_version INTEGER NOT NULL CHECK(submission_contract_version >= 2),
    revision_id TEXT NOT NULL UNIQUE,
    revision_snapshot_json TEXT NOT NULL,
    revision_snapshot_sha256 TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY(
        course_id,
        source_id,
        source_commit_hash,
        sequence,
        attempt_number,
        submission_contract_version
    ),
    UNIQUE(batch_id, attempt_number, submission_contract_version)
);

CREATE INDEX idx_course_submission_revision_reservations_batch
ON course_progression_submission_revision_reservations(
    batch_id, attempt_number, submission_contract_version
);
