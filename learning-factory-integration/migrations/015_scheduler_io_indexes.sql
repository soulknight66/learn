-- Keep the high-frequency scheduler paths on compact indexes. The jobs table
-- contains multi-kilobyte payloads, so a non-covering state scan otherwise
-- pulls most of that table across NFS merely to obtain job IDs.
CREATE INDEX idx_jobs_state_job_id
ON jobs(state,job_id);

-- Match the deterministic claim order after the two equality predicates. The
-- scheduler reads candidates in bounded pages and fetches the complete row only
-- after choosing one.
CREATE INDEX idx_jobs_claim_order
ON jobs(state,cancel_requested,priority DESC,created_at,job_id);
