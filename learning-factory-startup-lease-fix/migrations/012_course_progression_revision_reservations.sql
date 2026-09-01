CREATE TABLE course_progression_revision_reservations (
    course_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_commit_hash TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK(sequence > 0),
    batch_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK(attempt_number >= 2),
    revision_id TEXT NOT NULL UNIQUE,
    revision_snapshot_json TEXT NOT NULL,
    revision_snapshot_sha256 TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY(
        course_id,
        source_id,
        source_commit_hash,
        sequence,
        attempt_number
    ),
    UNIQUE(batch_id, attempt_number)
);

CREATE INDEX idx_course_progression_revision_reservations_batch
ON course_progression_revision_reservations(batch_id, attempt_number);
