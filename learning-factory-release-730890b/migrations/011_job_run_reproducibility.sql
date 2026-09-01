ALTER TABLE job_runs ADD COLUMN reproducibility_digest TEXT;
ALTER TABLE job_runs ADD COLUMN reproducibility_path TEXT;
ALTER TABLE job_runs ADD COLUMN reproducibility_json TEXT NOT NULL DEFAULT '{}';

CREATE INDEX idx_job_runs_reproducibility_digest
ON job_runs(reproducibility_digest);
