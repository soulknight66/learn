-- SQLite 3.26 cannot push a composite row-value bound through an expression
-- index. Persist the equivalent ascending priority key so even a large group
-- of equal-priority jobs can use the complete continuation tuple.
ALTER TABLE jobs ADD COLUMN claim_priority_key REAL;

UPDATE jobs SET claim_priority_key=(-priority);

CREATE TRIGGER jobs_claim_priority_insert
AFTER INSERT ON jobs
BEGIN
    UPDATE jobs SET claim_priority_key=(-NEW.priority)
    WHERE job_id=NEW.job_id;
END;

CREATE TRIGGER jobs_claim_priority_update
AFTER UPDATE OF priority ON jobs
BEGIN
    UPDATE jobs SET claim_priority_key=(-NEW.priority)
    WHERE job_id=NEW.job_id;
END;

CREATE TRIGGER jobs_claim_priority_guard
BEFORE UPDATE OF claim_priority_key ON jobs
WHEN NEW.claim_priority_key IS NULL
  OR NEW.claim_priority_key <> (-NEW.priority)
BEGIN
    SELECT RAISE(ABORT, 'invalid claim priority key');
END;

CREATE INDEX idx_jobs_claim_cursor
ON jobs(state,cancel_requested,claim_priority_key,created_at,job_id);

-- A preselected job may be claimed only while the scheduling projection used
-- to choose it is unchanged.  Heartbeats deliberately do not advance this
-- generation because their lease timestamps do not affect READY order or
-- worker-type capacity.
CREATE TABLE scheduler_generations (
    name TEXT PRIMARY KEY,
    generation INTEGER NOT NULL CHECK(generation >= 0)
);

INSERT INTO scheduler_generations(name,generation)
VALUES ('jobs_claim_projection',0);

CREATE TRIGGER jobs_claim_generation_insert
AFTER INSERT ON jobs
BEGIN
    UPDATE scheduler_generations
    SET generation=generation+1
    WHERE name='jobs_claim_projection';
END;

CREATE TRIGGER jobs_claim_generation_delete
AFTER DELETE ON jobs
BEGIN
    UPDATE scheduler_generations
    SET generation=generation+1
    WHERE name='jobs_claim_projection';
END;

CREATE TRIGGER jobs_claim_generation_update
AFTER UPDATE OF state,cancel_requested,attempt_count,max_attempts,
                job_id,worker_type,priority,created_at,payload_json ON jobs
BEGIN
    UPDATE scheduler_generations
    SET generation=generation+1
    WHERE name='jobs_claim_projection';
END;

-- Dependency edges are part of the claim projection.  A job can become
-- claimable (or cease to be claimable) when an edge is removed, retargeted,
-- or added, so every edge mutation invalidates a preselected candidate.
-- New dependencies are immutable once a child leaves DISCOVERED.  Deletion
-- intentionally remains unguarded so ON DELETE CASCADE can do its work.
CREATE TRIGGER job_dependencies_insert_guard
BEFORE INSERT ON job_dependencies
WHEN NOT EXISTS (
    SELECT 1 FROM jobs child
    WHERE child.job_id=NEW.job_id AND child.state='DISCOVERED'
)
BEGIN
    SELECT RAISE(ABORT, 'dependencies may only be added to DISCOVERED jobs');
END;

CREATE TRIGGER job_dependencies_update_guard
BEFORE UPDATE OF job_id,depends_on_job_id ON job_dependencies
WHEN (OLD.job_id <> NEW.job_id OR OLD.depends_on_job_id <> NEW.depends_on_job_id)
  AND (
      NOT EXISTS (
          SELECT 1 FROM jobs old_child
          WHERE old_child.job_id=OLD.job_id AND old_child.state='DISCOVERED'
      )
      OR NOT EXISTS (
          SELECT 1 FROM jobs new_child
          WHERE new_child.job_id=NEW.job_id AND new_child.state='DISCOVERED'
      )
  )
BEGIN
    SELECT RAISE(ABORT, 'dependencies may only be changed between DISCOVERED jobs');
END;

-- A direct edge deletion or deletion of a prerequisite must not weaken the
-- graph of a queued, active, or terminal child. During ON DELETE CASCADE for
-- deletion of the child itself, SQLite has already made that child invisible
-- to this trigger, so whole-child cleanup remains legal.
CREATE TRIGGER job_dependencies_delete_guard
BEFORE DELETE ON job_dependencies
WHEN EXISTS (
    SELECT 1 FROM jobs child
    WHERE child.job_id=OLD.job_id AND child.state <> 'DISCOVERED'
)
BEGIN
    SELECT RAISE(ABORT, 'dependencies may only be removed from DISCOVERED jobs');
END;

CREATE TRIGGER job_dependencies_claim_generation_insert
AFTER INSERT ON job_dependencies
BEGIN
    UPDATE scheduler_generations
    SET generation=generation+1
    WHERE name='jobs_claim_projection';
END;

CREATE TRIGGER job_dependencies_claim_generation_delete
AFTER DELETE ON job_dependencies
BEGIN
    UPDATE scheduler_generations
    SET generation=generation+1
    WHERE name='jobs_claim_projection';
END;

CREATE TRIGGER job_dependencies_claim_generation_update
AFTER UPDATE OF job_id,depends_on_job_id ON job_dependencies
BEGIN
    UPDATE scheduler_generations
    SET generation=generation+1
    WHERE name='jobs_claim_projection';
END;

-- Repository code performs the same check before publishing an artifact and
-- in its final state update.  Keep the database invariant authoritative for
-- any future writer that attempts to bypass that API.
CREATE TRIGGER jobs_success_requires_succeeded_dependencies
BEFORE UPDATE OF state ON jobs
WHEN OLD.state <> 'SUCCEEDED' AND NEW.state='SUCCEEDED'
  AND EXISTS (
      SELECT 1
      FROM job_dependencies dependency
      LEFT JOIN jobs prerequisite
        ON prerequisite.job_id=dependency.depends_on_job_id
      WHERE dependency.job_id=NEW.job_id
        AND (
            prerequisite.job_id IS NULL
            OR prerequisite.state <> 'SUCCEEDED'
        )
  )
BEGIN
    SELECT RAISE(ABORT, 'cannot succeed job with unsatisfied dependencies');
END;
