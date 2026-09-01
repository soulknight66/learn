CREATE TABLE learner_attempt_invalidations (
    invalidation_id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL UNIQUE REFERENCES attempts(attempt_id),
    source_job_id TEXT NOT NULL REFERENCES jobs(job_id),
    reason TEXT NOT NULL,
    replacement_policy TEXT NOT NULL,
    invalidated_at REAL NOT NULL
);

CREATE INDEX idx_learner_attempt_invalidations_source_job
ON learner_attempt_invalidations(source_job_id);

CREATE TABLE learner_evidence_invalidations (
    invalidation_id TEXT PRIMARY KEY,
    evidence_id TEXT NOT NULL UNIQUE REFERENCES knowledge_evidence(evidence_id),
    attempt_id TEXT NOT NULL REFERENCES attempts(attempt_id),
    source_job_id TEXT NOT NULL REFERENCES jobs(job_id),
    reason TEXT NOT NULL,
    invalidated_at REAL NOT NULL
);

CREATE INDEX idx_learner_evidence_invalidations_attempt
ON learner_evidence_invalidations(attempt_id);
