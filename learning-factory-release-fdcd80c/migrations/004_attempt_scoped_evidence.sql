ALTER TABLE validations ADD COLUMN attempt_number INTEGER NOT NULL DEFAULT 0;
ALTER TABLE validations ADD COLUMN claims_json TEXT NOT NULL DEFAULT '[]';

-- Legacy rows cannot be assigned safely from job_id alone: a job may have run
-- more than once. Keep them in attempt 0 so they cannot authorize a future
-- completion. New validators always record the exact claimed attempt.

CREATE INDEX idx_validations_job_attempt
ON validations(job_id, attempt_number, status);

ALTER TABLE artifacts ADD COLUMN attempt_number INTEGER NOT NULL DEFAULT 0;

UPDATE artifacts
SET attempt_number = COALESCE(
    CAST(json_extract(metadata_json, '$.attempt') AS INTEGER),
    (SELECT MAX(r.attempt_number) FROM job_runs r WHERE r.job_id=artifacts.job_id),
    0
);

-- Migration 003 intentionally bootstrapped discoverability, but its generic
-- name-based backfill was too optimistic. Rebuild historical labels from
-- conservative, explicitly reviewed evidence.
DELETE FROM artifact_validation_labels;

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT artifact_id,'GENERATED','{"classification":"archive-created"}',created_at
FROM artifacts;

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT artifact_id,'BUILDS','{"review":"meta-evaluation-001","scope":"python syntax"}',created_at
FROM artifacts WHERE job_id IN ('job_course_mit6s081_vertical','job_project_kvstore_vertical');

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT artifact_id,'TESTED','{"review":"meta-evaluation-001","scope":"bounded deterministic suites"}',created_at
FROM artifacts WHERE job_id IN ('job_course_mit6s081_vertical','job_project_kvstore_vertical');

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT artifact_id,'TRANSFER_VERIFIED','{"review":"meta-evaluation-001","scope":"python semantic model only"}',created_at
FROM artifacts WHERE job_id='job_course_mit6s081_vertical';

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT artifact_id,'FUZZED','{"review":"meta-evaluation-001","scope":"fixed-seed bounded model fuzz"}',created_at
FROM artifacts WHERE job_id='job_project_kvstore_vertical';

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT artifact_id,'BENCHMARKED','{"review":"meta-evaluation-001","scope":"single smoke measurement; no performance conclusion"}',created_at
FROM artifacts WHERE job_id='job_project_kvstore_vertical';

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT artifact_id,'PARTIAL','{"review":"meta-evaluation-001","reason":"negative-path durability defects; not production-ready"}',created_at
FROM artifacts WHERE job_id='job_project_kvstore_vertical';

UPDATE artifacts
SET validation_status = COALESCE(
    (
        SELECT group_concat(ordered.label, '+')
        FROM (
            SELECT label
            FROM artifact_validation_labels labels
            WHERE labels.artifact_id=artifacts.artifact_id
            ORDER BY CASE label
                WHEN 'GENERATED' THEN 1 WHEN 'BUILDS' THEN 2 WHEN 'TESTED' THEN 3
                WHEN 'FUZZED' THEN 4 WHEN 'BENCHMARKED' THEN 5
                WHEN 'TRANSFER_VERIFIED' THEN 6 WHEN 'PARTIAL' THEN 7 ELSE 99 END
        ) AS ordered
    ),
    'GENERATED'
);
