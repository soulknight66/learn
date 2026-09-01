BEGIN IMMEDIATE;

CREATE TABLE allowed_transitions (
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    PRIMARY KEY (from_state, to_state)
);

INSERT INTO allowed_transitions (from_state, to_state) VALUES
    ('CREATED', 'RUNNING'),
    ('CREATED', 'DELETED'),
    ('RUNNING', 'EXITED'),
    ('RUNNING', 'FAILED'),
    ('EXITED', 'RUNNING'),
    ('EXITED', 'DELETED'),
    ('FAILED', 'RUNNING'),
    ('FAILED', 'DELETED');

CREATE TABLE containers (
    container_id TEXT PRIMARY KEY,
    spec_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('CREATED', 'RUNNING', 'EXITED', 'FAILED', 'DELETED')),
    exit_code INTEGER,
    created_ns INTEGER NOT NULL CHECK (created_ns >= 0),
    updated_ns INTEGER NOT NULL CHECK (updated_ns >= created_ns),
    CHECK ((state = 'EXITED' AND exit_code IS NOT NULL) OR (state <> 'EXITED' AND exit_code IS NULL))
);

CREATE TABLE state_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    container_id TEXT NOT NULL REFERENCES containers(container_id),
    from_state TEXT,
    to_state TEXT NOT NULL,
    exit_code INTEGER,
    at_ns INTEGER NOT NULL CHECK (at_ns >= 0)
);

CREATE TRIGGER enforce_container_transition
BEFORE UPDATE OF state ON containers
FOR EACH ROW
WHEN OLD.state <> NEW.state
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM allowed_transitions
        WHERE from_state = OLD.state AND to_state = NEW.state
    ) THEN RAISE(ABORT, 'invalid container state transition') END;
END;

CREATE TRIGGER record_container_transition
AFTER UPDATE OF state ON containers
FOR EACH ROW
WHEN OLD.state <> NEW.state
BEGIN
    INSERT INTO state_events (container_id, from_state, to_state, exit_code, at_ns)
    VALUES (NEW.container_id, OLD.state, NEW.state, NEW.exit_code, NEW.updated_ns);
END;

PRAGMA user_version = 1;
COMMIT;
