ALTER TABLE jobs ADD COLUMN lease_token TEXT;

CREATE TRIGGER require_active_lease_token_on_insert
BEFORE INSERT ON jobs
WHEN NEW.state IN ('CLAIMED','RUNNING') AND NEW.lease_token IS NULL
BEGIN
    SELECT RAISE(ABORT, 'active job requires lease token');
END;

CREATE TRIGGER require_active_lease_token_on_update
BEFORE UPDATE ON jobs
WHEN NEW.state IN ('CLAIMED','RUNNING') AND NEW.lease_token IS NULL
BEGIN
    SELECT RAISE(ABORT, 'active job requires lease token');
END;
