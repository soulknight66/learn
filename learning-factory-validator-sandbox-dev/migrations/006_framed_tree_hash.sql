ALTER TABLE artifacts
ADD COLUMN checksum_algorithm TEXT NOT NULL DEFAULT 'tree-sha256-v1'
CHECK(checksum_algorithm IN ('tree-sha256-v1','tree-sha256-v2'));
