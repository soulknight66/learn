CREATE TRIGGER validate_job_id_insert
BEFORE INSERT ON jobs
WHEN length(NEW.job_id) < 5
  OR length(NEW.job_id) > 160
  OR substr(NEW.job_id, 1, 4) <> 'job_'
  OR substr(NEW.job_id, 5) GLOB '*[^A-Za-z0-9_.-]*'
BEGIN
    SELECT RAISE(ABORT, 'invalid job id');
END;

CREATE TRIGGER validate_job_id_update
BEFORE UPDATE OF job_id ON jobs
WHEN length(NEW.job_id) < 5
  OR length(NEW.job_id) > 160
  OR substr(NEW.job_id, 1, 4) <> 'job_'
  OR substr(NEW.job_id, 5) GLOB '*[^A-Za-z0-9_.-]*'
BEGIN
    SELECT RAISE(ABORT, 'invalid job id');
END;
