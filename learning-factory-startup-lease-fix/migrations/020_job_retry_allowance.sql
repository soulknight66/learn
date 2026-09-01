-- Keep configured max_attempts immutable for baseline-bound BYOX jobs while
-- allowing durable, operator-authorized retries and graceful interruption.
-- This is runtime state and is deliberately excluded from job-definition
-- digests and the migration-019 immutable-definition trigger.
ALTER TABLE jobs
ADD COLUMN retry_allowance INTEGER NOT NULL DEFAULT 0
    CHECK(typeof(retry_allowance)='integer' AND retry_allowance >= 0);

-- A controller action may authorize exactly one additional future attempt.
-- Allowance is monotonic and may only be granted while manually reopening a
-- terminal/blocked job or preserving an in-flight job during interruption.
CREATE TRIGGER job_retry_allowance_guard
BEFORE UPDATE OF retry_allowance ON jobs
WHEN NEW.retry_allowance <> OLD.retry_allowance
 AND (
      NEW.retry_allowance <> OLD.retry_allowance + 1
      OR NOT (
          (OLD.state IN ('FAILED','BLOCKED') AND NEW.state='READY')
          OR
          (OLD.state IN ('CLAIMED','RUNNING') AND NEW.state='RETRY_WAIT')
      )
 )
BEGIN
    SELECT RAISE(ABORT, 'retry allowance requires one controller-authorized attempt');
END;
