ALTER TABLE artifacts
ADD COLUMN integrity_status TEXT NOT NULL DEFAULT 'LEGACY_UNVERIFIED'
CHECK(integrity_status IN ('LEGACY_UNVERIFIED','VERIFIED_V2'));

-- Migration 006 began recording the unambiguous framed hash before this
-- integrity column existed. Preserve that evidence instead of accidentally
-- quarantining already-published v2 artifacts as legacy.
UPDATE artifacts
SET integrity_status='VERIFIED_V2'
WHERE checksum_algorithm='tree-sha256-v2';

INSERT OR IGNORE INTO artifact_validation_labels(
    artifact_id,label,evidence_json,created_at
)
SELECT artifact_id,'PARTIAL',
       '{"reason":"legacy unframed tree hash is structurally ambiguous; artifact is preserved but non-stageable"}',
       created_at
FROM artifacts
WHERE checksum_algorithm='tree-sha256-v1';

UPDATE artifacts
SET validation_status = COALESCE(
    (
        SELECT group_concat(ordered.label, '+')
        FROM (
            SELECT label
            FROM artifact_validation_labels labels
            WHERE labels.artifact_id=artifacts.artifact_id
            ORDER BY CASE label
                WHEN 'GENERATED' THEN 1 WHEN 'BUILDS' THEN 2 WHEN 'TESTED' THEN 3
                WHEN 'FUZZED' THEN 4 WHEN 'BENCHMARKED' THEN 5 WHEN 'REVIEWED' THEN 6
                WHEN 'TRANSFER_VERIFIED' THEN 7 WHEN 'PRODUCTIONIZED' THEN 8
                WHEN 'PARTIAL' THEN 9 ELSE 99 END
        ) AS ordered
    ),
    'PARTIAL'
)
WHERE checksum_algorithm='tree-sha256-v1';
