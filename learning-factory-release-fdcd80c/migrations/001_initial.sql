PRAGMA foreign_keys = ON;

CREATE TABLE sources (
    source_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    upstream_url TEXT,
    commit_hash TEXT NOT NULL,
    license TEXT,
    ingested_at REAL NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(path, commit_hash)
);

CREATE TABLE courses (
    course_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    slug TEXT NOT NULL,
    institution TEXT,
    title TEXT NOT NULL,
    topic TEXT,
    description TEXT,
    prerequisites_json TEXT NOT NULL DEFAULT '[]',
    estimated_human_hours REAL,
    difficulty REAL,
    source_metadata_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'DISCOVERED',
    UNIQUE(source_id, slug)
);

CREATE TABLE course_units (
    unit_id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    unit_order INTEGER NOT NULL,
    title TEXT NOT NULL,
    dependencies_json TEXT NOT NULL DEFAULT '[]',
    source_reference TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(course_id, unit_order, title)
);

CREATE TABLE curriculum_edges (
    from_course_id TEXT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    to_course_id TEXT NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    evidence TEXT,
    inferred INTEGER NOT NULL CHECK(inferred IN (0,1)),
    PRIMARY KEY(from_course_id, to_course_id, relation)
);

CREATE TABLE build_projects (
    project_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    slug TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    implementation_language TEXT,
    upstream_reference TEXT NOT NULL,
    concepts_json TEXT NOT NULL DEFAULT '[]',
    difficulty REAL,
    production_relevance REAL,
    source_format TEXT,
    priority_tier INTEGER NOT NULL DEFAULT 3,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(source_id, upstream_reference)
);

CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    persona TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    current_state_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE attempts (
    attempt_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES students(student_id),
    task_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL,
    result TEXT,
    workspace TEXT,
    UNIQUE(student_id, task_id, attempt_number)
);

CREATE TABLE allowed_job_transitions (
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    PRIMARY KEY(from_state, to_state)
);

INSERT INTO allowed_job_transitions VALUES
 ('DISCOVERED','READY'), ('DISCOVERED','BLOCKED'), ('DISCOVERED','CANCELLED'),
 ('READY','CLAIMED'), ('READY','BLOCKED'), ('READY','CANCELLED'),
 ('CLAIMED','RUNNING'), ('CLAIMED','RETRY_WAIT'), ('CLAIMED','FAILED'), ('CLAIMED','CANCELLED'),
 ('RUNNING','SUCCEEDED'), ('RUNNING','RETRY_WAIT'), ('RUNNING','BLOCKED'), ('RUNNING','FAILED'), ('RUNNING','CANCELLED'),
 ('RETRY_WAIT','READY'), ('RETRY_WAIT','FAILED'), ('RETRY_WAIT','CANCELLED'),
 ('BLOCKED','READY'), ('BLOCKED','CANCELLED'),
 ('FAILED','READY'), ('FAILED','CANCELLED');

CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    worker_type TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('DISCOVERED','READY','CLAIMED','RUNNING','SUCCEEDED','RETRY_WAIT','BLOCKED','FAILED','CANCELLED')),
    priority REAL NOT NULL DEFAULT 0,
    score_components_json TEXT NOT NULL DEFAULT '{}',
    payload_json TEXT NOT NULL DEFAULT '{}',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK(max_attempts > 0),
    owner TEXT,
    lease_expires_at REAL,
    heartbeat_at REAL,
    retry_at REAL,
    created_at REAL NOT NULL,
    started_at REAL,
    finished_at REAL,
    error TEXT,
    failure_kind TEXT,
    workspace TEXT,
    cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK(cancel_requested IN (0,1)),
    model TEXT,
    reasoning_effort TEXT,
    CHECK((state IN ('CLAIMED','RUNNING') AND owner IS NOT NULL AND lease_expires_at IS NOT NULL) OR state NOT IN ('CLAIMED','RUNNING'))
);

CREATE TRIGGER enforce_job_state_transition
BEFORE UPDATE OF state ON jobs
WHEN OLD.state <> NEW.state
BEGIN
    SELECT CASE WHEN NOT EXISTS (
        SELECT 1 FROM allowed_job_transitions
        WHERE from_state = OLD.state AND to_state = NEW.state
    ) THEN RAISE(ABORT, 'invalid job state transition') END;
END;

CREATE TABLE job_dependencies (
    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    depends_on_job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
    PRIMARY KEY(job_id, depends_on_job_id),
    CHECK(job_id <> depends_on_job_id)
);

CREATE TABLE workers (
    worker_id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    process_id INTEGER,
    thread_id TEXT,
    workspace TEXT,
    state TEXT NOT NULL,
    started_at REAL NOT NULL,
    last_activity REAL NOT NULL,
    current_job TEXT REFERENCES jobs(job_id),
    hostname TEXT,
    error TEXT
);

CREATE TABLE job_runs (
    run_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    worker_id TEXT REFERENCES workers(worker_id),
    attempt_number INTEGER NOT NULL,
    backend TEXT NOT NULL,
    model TEXT,
    reasoning_effort TEXT,
    session_id TEXT,
    process_id INTEGER,
    started_at REAL NOT NULL,
    finished_at REAL,
    exit_code INTEGER,
    stdout_path TEXT,
    stderr_path TEXT,
    usage_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    type TEXT NOT NULL,
    path TEXT NOT NULL,
    checksum TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    validation_status TEXT NOT NULL,
    UNIQUE(job_id, type, checksum)
);

CREATE TABLE evaluations (
    evaluation_id TEXT PRIMARY KEY,
    attempt_id TEXT REFERENCES attempts(attempt_id),
    job_id TEXT REFERENCES jobs(job_id),
    evaluator TEXT NOT NULL,
    rubric_json TEXT NOT NULL,
    result TEXT NOT NULL,
    score REAL,
    evidence_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    CHECK(attempt_id IS NOT NULL OR job_id IS NOT NULL)
);

CREATE TABLE learner_knowledge (
    student_id TEXT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    concept TEXT NOT NULL,
    confidence REAL NOT NULL CHECK(confidence >= 0 AND confidence <= 1),
    misconceptions_json TEXT NOT NULL DEFAULT '[]',
    last_updated REAL NOT NULL,
    PRIMARY KEY(student_id, concept)
);

CREATE TABLE knowledge_evidence (
    evidence_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    concept TEXT NOT NULL,
    kind TEXT NOT NULL,
    description TEXT NOT NULL,
    source_reference TEXT,
    weight REAL NOT NULL,
    created_at REAL NOT NULL,
    FOREIGN KEY(student_id, concept) REFERENCES learner_knowledge(student_id, concept) ON DELETE CASCADE
);

CREATE TABLE validations (
    validation_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(job_id),
    validator TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PASS','FAIL','ERROR')),
    command_json TEXT,
    exit_code INTEGER,
    stdout_path TEXT,
    stderr_path TEXT,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    started_at REAL NOT NULL,
    finished_at REAL NOT NULL
);

CREATE TABLE events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    actor TEXT NOT NULL,
    job_id TEXT REFERENCES jobs(job_id),
    worker_id TEXT REFERENCES workers(worker_id),
    type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE system_state (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    labels_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_jobs_schedulable ON jobs(state, retry_at, priority DESC, created_at);
CREATE INDEX idx_jobs_lease ON jobs(state, lease_expires_at);
CREATE INDEX idx_events_job ON events(job_id, event_id);
CREATE INDEX idx_workers_state ON workers(state, type);
CREATE INDEX idx_courses_topic ON courses(topic, status);
CREATE INDEX idx_projects_category ON build_projects(category, priority_tier);

INSERT INTO system_state(key, value_json, updated_at) VALUES ('paused', 'false', strftime('%s','now'));

