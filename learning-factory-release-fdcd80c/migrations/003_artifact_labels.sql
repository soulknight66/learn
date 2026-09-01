CREATE TABLE artifact_validation_labels (
    artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id) ON DELETE CASCADE,
    label TEXT NOT NULL CHECK(label IN (
        'GENERATED','BUILDS','TESTED','FUZZED','BENCHMARKED','REVIEWED',
        'TRANSFER_VERIFIED','PRODUCTIONIZED','PARTIAL','BLOCKED'
    )),
    evidence_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    PRIMARY KEY(artifact_id, label)
);

CREATE INDEX idx_artifact_labels_label ON artifact_validation_labels(label, artifact_id);

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT artifact_id,'GENERATED','{"source":"migration-backfill"}',created_at FROM artifacts;

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT artifact_id,'TESTED','{"source":"passed-validation-records"}',created_at FROM artifacts;

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT DISTINCT a.artifact_id,'BUILDS','{"source":"validator-name"}',a.created_at
FROM artifacts a JOIN validations v ON v.job_id=a.job_id
WHERE v.status='PASS' AND (lower(v.validator) LIKE '%build%' OR lower(v.validator) LIKE '%syntax%' OR lower(v.validator) LIKE '%compile%');

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT DISTINCT a.artifact_id,'FUZZED','{"source":"validator-name"}',a.created_at
FROM artifacts a JOIN validations v ON v.job_id=a.job_id
WHERE v.status='PASS' AND lower(v.validator) LIKE '%fuzz%';

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT DISTINCT a.artifact_id,'BENCHMARKED','{"source":"validator-name"}',a.created_at
FROM artifacts a JOIN validations v ON v.job_id=a.job_id
WHERE v.status='PASS' AND lower(v.validator) LIKE '%benchmark%';

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT DISTINCT a.artifact_id,'PRODUCTIONIZED','{"source":"validator-name"}',a.created_at
FROM artifacts a JOIN validations v ON v.job_id=a.job_id
WHERE v.status='PASS' AND lower(v.validator) LIKE '%production%';

INSERT INTO artifact_validation_labels(artifact_id,label,evidence_json,created_at)
SELECT DISTINCT a.artifact_id,'TRANSFER_VERIFIED','{"source":"validator-name"}',a.created_at
FROM artifacts a JOIN validations v ON v.job_id=a.job_id
WHERE v.status='PASS' AND lower(v.validator) LIKE '%transfer%';

UPDATE artifacts
SET validation_status = (
    SELECT group_concat(label, '+')
    FROM artifact_validation_labels labels
    WHERE labels.artifact_id=artifacts.artifact_id
);
