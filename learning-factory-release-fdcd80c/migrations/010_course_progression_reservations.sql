CREATE TABLE course_progression_reservations (
    course_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_commit_hash TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK(sequence > 0),
    batch_id TEXT NOT NULL UNIQUE,
    batch_snapshot_json TEXT NOT NULL,
    batch_snapshot_sha256 TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY(course_id, source_id, source_commit_hash, sequence)
);

CREATE INDEX idx_course_progression_reservations_batch
ON course_progression_reservations(batch_id);
