-- Append-only observations produced when archived Build-Your-Own-X challenge
-- packs are replayed through the current structural code-presence policy.
-- These rows deliberately do not participate in artifact validation labels:
-- code presence is not evidence that a project builds or passes tests.
CREATE TABLE byox_code_presence_audits (
    audit_id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    artifact_attempt INTEGER NOT NULL,
    artifact_type TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    artifact_checksum TEXT NOT NULL,
    checksum_algorithm TEXT NOT NULL,
    integrity_status TEXT NOT NULL,
    job_state TEXT NOT NULL,
    job_attempt_count INTEGER NOT NULL,
    job_payload_sha256 TEXT NOT NULL,
    policy_name TEXT NOT NULL,
    policy_digest TEXT NOT NULL,
    policy_spec_sha256 TEXT NOT NULL,
    policy_spec_json TEXT NOT NULL,
    observation_sha256 TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK(outcome IN ('PASS','FAIL','ERROR','CONFLICT')),
    gate_status TEXT NOT NULL CHECK(gate_status IN ('PASS','FAIL','ERROR','NOT_RUN')),
    scope TEXT NOT NULL CHECK(scope='CODE_PRESENCE_STRUCTURE_ONLY'),
    semantic_claims_json TEXT NOT NULL CHECK(semantic_claims_json='[]'),
    observed_checksum TEXT,
    controller_evidence_sha256 TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE(artifact_id, policy_name, policy_digest, observation_sha256),
    CHECK(outcome <> 'PASS' OR (
        gate_status='PASS'
        AND checksum_algorithm='tree-sha256-v2'
        AND integrity_status='VERIFIED_V2'
        AND observed_checksum=artifact_checksum
    ))
);

CREATE INDEX idx_byox_code_audits_policy_outcome
ON byox_code_presence_audits(policy_name,policy_digest,outcome,artifact_id);

CREATE INDEX idx_byox_code_audits_artifact
ON byox_code_presence_audits(artifact_id,created_at,audit_id);

-- Bind each inserted observation to the exact authoritative artifact row that
-- existed at insertion time. Later artifact deletion is also prevented by the
-- foreign key above, retaining the evidence target.
CREATE TRIGGER bind_byox_code_audit_artifact_insert
BEFORE INSERT ON byox_code_presence_audits
WHEN NOT EXISTS (
    SELECT 1 FROM artifacts AS artifact
    WHERE artifact.artifact_id=NEW.artifact_id
      AND artifact.job_id=NEW.job_id
      AND artifact.attempt_number=NEW.artifact_attempt
      AND artifact.type=NEW.artifact_type
      AND artifact.path=NEW.artifact_path
      AND artifact.checksum=NEW.artifact_checksum
      AND artifact.checksum_algorithm=NEW.checksum_algorithm
      AND artifact.integrity_status=NEW.integrity_status
)
BEGIN
    SELECT RAISE(ABORT, 'BYOX code audit artifact binding mismatch');
END;

CREATE TRIGGER bind_byox_code_audit_job_insert
BEFORE INSERT ON byox_code_presence_audits
WHEN NOT EXISTS (
    SELECT 1 FROM jobs AS job
    WHERE job.job_id=NEW.job_id
      AND job.state=NEW.job_state
      AND job.attempt_count=NEW.job_attempt_count
)
BEGIN
    SELECT RAISE(ABORT, 'BYOX code audit job binding mismatch');
END;

CREATE TRIGGER forbid_byox_code_audit_update
BEFORE UPDATE ON byox_code_presence_audits
BEGIN
    SELECT RAISE(ABORT, 'BYOX code audits are append-only');
END;

CREATE TRIGGER forbid_byox_code_audit_delete
BEFORE DELETE ON byox_code_presence_audits
BEGIN
    SELECT RAISE(ABORT, 'BYOX code audits are append-only');
END;
