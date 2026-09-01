ALTER TABLE job_runs ADD COLUMN provider TEXT;
ALTER TABLE job_runs ADD COLUMN base_url TEXT;
ALTER TABLE job_runs ADD COLUMN wire_api TEXT;
ALTER TABLE job_runs ADD COLUMN supports_websockets INTEGER
CHECK(supports_websockets IS NULL OR supports_websockets IN (0,1));
