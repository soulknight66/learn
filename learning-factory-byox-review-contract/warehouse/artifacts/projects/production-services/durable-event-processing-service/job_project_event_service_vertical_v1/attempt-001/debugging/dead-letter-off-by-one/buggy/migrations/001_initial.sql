CREATE TABLE messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('READY','CLAIMED','RETRY_WAIT','DONE','DEAD')),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    available_at REAL NOT NULL,
    lease_owner TEXT,
    lease_token TEXT,
    lease_expires_at REAL,
    last_error TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    dead_lettered_at REAL,
    CHECK (
        (state = 'CLAIMED' AND lease_owner IS NOT NULL AND lease_token IS NOT NULL
                           AND lease_expires_at IS NOT NULL)
        OR
        (state <> 'CLAIMED' AND lease_owner IS NULL AND lease_token IS NULL
                            AND lease_expires_at IS NULL)
    )
);

CREATE INDEX messages_dispatch
    ON messages(state, available_at, message_id);

CREATE TABLE effects (
    message_id INTEGER PRIMARY KEY REFERENCES messages(message_id),
    effect_key TEXT NOT NULL UNIQUE,
    result_json TEXT NOT NULL,
    applied_at REAL NOT NULL
);

CREATE TABLE dead_letters (
    dead_letter_id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL REFERENCES messages(message_id),
    payload_json TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    reason TEXT NOT NULL,
    dead_lettered_at REAL NOT NULL,
    requeued_at REAL
);

CREATE UNIQUE INDEX dead_letters_one_active
    ON dead_letters(message_id) WHERE requeued_at IS NULL;

CREATE INDEX dead_letters_page
    ON dead_letters(requeued_at, dead_letter_id);
