-- Preserve the controller-derived material baseline independently from mutable
-- source observations and job payloads.  SQLite cannot calculate SHA-256, so
-- application code recomputes and verifies every material/definition digest.
CREATE TABLE byox_baseline_snapshots (
    baseline_sha256 TEXT PRIMARY KEY
        CHECK(
            length(baseline_sha256)=64
            AND baseline_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    schema_version INTEGER NOT NULL CHECK(schema_version=1),
    project_id TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    source_commit_hash TEXT NOT NULL CHECK(length(source_commit_hash)>0),
    extractor_version TEXT NOT NULL CHECK(length(extractor_version)>0),
    material_json TEXT NOT NULL
        CHECK(json_valid(material_json) AND json_type(material_json)='object'),
    first_observed_at REAL NOT NULL CHECK(first_observed_at>=0),
    UNIQUE(project_id,baseline_sha256)
);

CREATE INDEX idx_byox_baseline_project
ON byox_baseline_snapshots(project_id,first_observed_at,baseline_sha256);

CREATE TRIGGER byox_baseline_snapshots_immutable_update
BEFORE UPDATE ON byox_baseline_snapshots
BEGIN
    SELECT RAISE(ABORT, 'BYOX baseline snapshots are immutable');
END;

CREATE TRIGGER byox_baseline_snapshots_immutable_delete
BEFORE DELETE ON byox_baseline_snapshots
BEGIN
    SELECT RAISE(ABORT, 'BYOX baseline snapshots are immutable');
END;

-- A binding is written only after the job and its complete dependency set
-- exist.  definition_sha256 covers every immutable job-definition field and
-- the sorted dependency IDs; application code verifies it on every read.
CREATE TABLE byox_baseline_job_bindings (
    job_id TEXT PRIMARY KEY REFERENCES jobs(job_id),
    baseline_sha256 TEXT NOT NULL
        REFERENCES byox_baseline_snapshots(baseline_sha256),
    role TEXT NOT NULL CHECK(role IN ('builder','reviewer')),
    policy_version INTEGER NOT NULL CHECK(policy_version>0),
    builder_job_id TEXT REFERENCES jobs(job_id),
    definition_sha256 TEXT NOT NULL
        CHECK(
            length(definition_sha256)=64
            AND definition_sha256 NOT GLOB '*[^0-9a-f]*'
        ),
    bound_at REAL NOT NULL CHECK(bound_at>=0),
    CHECK(
        (role='builder' AND builder_job_id IS NULL)
        OR
        (role='reviewer' AND builder_job_id IS NOT NULL AND builder_job_id<>job_id)
    )
);

-- COALESCE makes the canonical builder tuple unique even though SQLite treats
-- NULL values as distinct in an ordinary UNIQUE constraint.
CREATE UNIQUE INDEX idx_byox_baseline_binding_identity
ON byox_baseline_job_bindings(
    baseline_sha256,
    role,
    policy_version,
    COALESCE(builder_job_id,'')
);

CREATE INDEX idx_byox_baseline_binding_builder
ON byox_baseline_job_bindings(builder_job_id,baseline_sha256);

CREATE TRIGGER byox_baseline_reviewer_requires_bound_builder
BEFORE INSERT ON byox_baseline_job_bindings
WHEN NEW.role='reviewer'
 AND NOT EXISTS (
    SELECT 1
    FROM byox_baseline_job_bindings builder
    WHERE builder.job_id=NEW.builder_job_id
      AND builder.baseline_sha256=NEW.baseline_sha256
      AND builder.role='builder'
 )
BEGIN
    SELECT RAISE(ABORT, 'BYOX reviewer requires a builder bound to the same baseline');
END;

CREATE TRIGGER byox_baseline_job_bindings_immutable_update
BEFORE UPDATE ON byox_baseline_job_bindings
BEGIN
    SELECT RAISE(ABORT, 'BYOX baseline job bindings are immutable');
END;

CREATE TRIGGER byox_baseline_job_bindings_immutable_delete
BEFORE DELETE ON byox_baseline_job_bindings
BEGIN
    SELECT RAISE(ABORT, 'BYOX baseline job bindings are immutable');
END;

-- Once bound, the definition may not be rewritten in place.  State, leases,
-- attempts, timestamps, and other runtime fields remain operationally mutable.
CREATE TRIGGER byox_bound_job_definition_immutable
BEFORE UPDATE OF
    job_id,type,worker_type,priority,score_components_json,payload_json,
    max_attempts,model,reasoning_effort
ON jobs
WHEN EXISTS (
    SELECT 1 FROM byox_baseline_job_bindings binding
    WHERE binding.job_id=OLD.job_id
)
BEGIN
    SELECT RAISE(ABORT, 'bound BYOX job definition is immutable');
END;

CREATE TRIGGER byox_bound_job_dependency_insert_guard
BEFORE INSERT ON job_dependencies
WHEN EXISTS (
    SELECT 1 FROM byox_baseline_job_bindings binding
    WHERE binding.job_id=NEW.job_id
)
BEGIN
    SELECT RAISE(ABORT, 'bound BYOX job dependencies are immutable');
END;

CREATE TRIGGER byox_bound_job_dependency_update_guard
BEFORE UPDATE OF job_id,depends_on_job_id ON job_dependencies
WHEN EXISTS (
        SELECT 1 FROM byox_baseline_job_bindings binding
        WHERE binding.job_id=OLD.job_id
     )
  OR EXISTS (
        SELECT 1 FROM byox_baseline_job_bindings binding
        WHERE binding.job_id=NEW.job_id
     )
BEGIN
    SELECT RAISE(ABORT, 'bound BYOX job dependencies are immutable');
END;

CREATE TRIGGER byox_bound_job_dependency_delete_guard
BEFORE DELETE ON job_dependencies
WHEN EXISTS (
    SELECT 1 FROM byox_baseline_job_bindings binding
    WHERE binding.job_id=OLD.job_id
)
BEGIN
    SELECT RAISE(ABORT, 'bound BYOX job dependencies are immutable');
END;
