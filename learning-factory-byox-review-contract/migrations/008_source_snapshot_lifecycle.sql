ALTER TABLE sources
ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1
CHECK(is_active IN (0,1));

ALTER TABLE sources
ADD COLUMN superseded_by_source_id TEXT REFERENCES sources(source_id);

ALTER TABLE sources
ADD COLUMN superseded_at REAL;

-- Older schemas allowed every commit observed at one canonical repository path
-- to look current.  Preserve every immutable snapshot and its normalized rows,
-- but select the most recently ingested snapshot as the sole active one.
UPDATE sources AS candidate
SET is_active = CASE
    WHEN candidate.source_id = (
        SELECT winner.source_id
        FROM sources AS winner
        WHERE winner.path=candidate.path
        ORDER BY winner.ingested_at DESC,winner.source_id DESC
        LIMIT 1
    ) THEN 1 ELSE 0 END;

UPDATE sources AS historical
SET superseded_by_source_id = (
        SELECT winner.source_id
        FROM sources AS winner
        WHERE winner.path=historical.path AND winner.is_active=1
        LIMIT 1
    ),
    superseded_at = (
        SELECT winner.ingested_at
        FROM sources AS winner
        WHERE winner.path=historical.path AND winner.is_active=1
        LIMIT 1
    )
WHERE historical.is_active=0;

CREATE UNIQUE INDEX idx_sources_one_active_snapshot_per_path
ON sources(path) WHERE is_active=1;

CREATE INDEX idx_sources_lifecycle
ON sources(path,is_active,ingested_at DESC);

CREATE TRIGGER source_active_snapshot_not_superseded_insert
BEFORE INSERT ON sources
WHEN NEW.is_active=1
 AND (NEW.superseded_by_source_id IS NOT NULL OR NEW.superseded_at IS NOT NULL)
BEGIN
    SELECT RAISE(ABORT, 'active source snapshot cannot be superseded');
END;

CREATE TRIGGER source_active_snapshot_not_superseded_update
BEFORE UPDATE ON sources
WHEN NEW.is_active=1
 AND (NEW.superseded_by_source_id IS NOT NULL OR NEW.superseded_at IS NOT NULL)
BEGIN
    SELECT RAISE(ABORT, 'active source snapshot cannot be superseded');
END;

CREATE TRIGGER source_snapshot_cannot_supersede_itself_insert
BEFORE INSERT ON sources
WHEN NEW.superseded_by_source_id=NEW.source_id
BEGIN
    SELECT RAISE(ABORT, 'source snapshot cannot supersede itself');
END;

CREATE TRIGGER source_snapshot_cannot_supersede_itself_update
BEFORE UPDATE ON sources
WHEN NEW.superseded_by_source_id=NEW.source_id
BEGIN
    SELECT RAISE(ABORT, 'source snapshot cannot supersede itself');
END;
