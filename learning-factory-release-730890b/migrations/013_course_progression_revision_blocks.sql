CREATE TABLE course_progression_revision_blocks (
    course_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_commit_hash TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK(sequence > 0),
    batch_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK(attempt_number >= 1),
    configured_revision_limit INTEGER NOT NULL CHECK(configured_revision_limit >= 0),
    evaluation_result TEXT NOT NULL CHECK(evaluation_result IN ('REVISE', 'FAIL')),
    reason TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY(batch_id, attempt_number, configured_revision_limit)
);
