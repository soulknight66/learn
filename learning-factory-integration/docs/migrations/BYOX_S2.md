# BYOX S2 migration note

Migrations `019_byox_baseline_snapshots.sql` and `020_job_retry_allowance.sql` move BYOX publication from
mutable, project-keyed seed rows to immutable material baselines and baseline-bound definitions.

Migration 019 adds:

- immutable content-v2 baseline snapshots;
- one definition-digest binding per baseline role and policy version;
- a same-baseline builder requirement for reviewers;
- SQL guards against changing bound definition fields or dependencies.

Migration 020 adds `jobs.retry_allowance` with a zero backfill. It is runtime state, not definition state.
The controller may grant one slot only during `FAILED|BLOCKED -> READY` or
`CLAIMED|RUNNING -> RETRY_WAIT`; configured `max_attempts` remains immutable.

Before applying, stop duplicate operators and back up SQLite plus the warehouse consistently. After
applying, run `seed-all` with the configured absolute warehouse. Exact queued legacy jobs are retired and
S2 is published in one transaction. Active legacy workers are asked to stop and defer publication.
Terminal rows are retained. Source relocation is accepted only when stored historical observations still
derive the same material baseline and the complete old definitions match released controller output.

Verification:

```bash
PYTHONPATH=src python3 -m unittest -q \
  tests.test_byox_baselines \
  tests.test_byox_s2_cutover \
  tests.test_byox_relocation_cutover \
  tests.test_byox_s2_remediation \
  tests.test_mass_seeding
```

Treat trigger failures, definition-digest failures, malformed legacy JSON, or partial binding graphs as
integrity failures. Do not update or delete the immutable tables to force progress. Restore the paired
pre-migration DB/warehouse backup for rollback, or correct the external source/configuration issue and
rerun the idempotent cutover.
