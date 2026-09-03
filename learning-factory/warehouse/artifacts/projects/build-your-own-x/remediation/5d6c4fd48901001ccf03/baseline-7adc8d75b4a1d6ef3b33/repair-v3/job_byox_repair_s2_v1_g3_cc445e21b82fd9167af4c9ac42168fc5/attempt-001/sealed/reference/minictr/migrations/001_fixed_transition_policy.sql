DROP TRIGGER IF EXISTS enforce_container_transition;
DROP TABLE IF EXISTS allowed_transitions;
CREATE TRIGGER enforce_container_transition
BEFORE UPDATE OF state ON containers
WHEN OLD.state <> NEW.state
BEGIN
    SELECT CASE WHEN NOT (
        (OLD.state = 'CREATED' AND NEW.state = 'RUNNING')
        OR (OLD.state = 'RUNNING' AND NEW.state IN ('EXITED', 'FAILED'))
    ) THEN RAISE(ABORT, 'invalid container state transition') END;
END;
