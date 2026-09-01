# Integrated-tip cutover rehearsal: GO

Rehearsed commit: `b2abec9ffe94cb02a610952bae2bb522141a8c37`

Repository: `/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory-integration`

Evidence root: `/projects/se/pj34000401_refsys/users/yuali01/learn/.integrated-tip-rehearsal.oPJyoxLp`

The Git worktree remained clean. No controller was started. Every operation that could write used
`warehouse/cutover-final.db`, a disposable SQLite backup. Every live-DB query used `sqlite3 -readonly`.

## Live boundary

- Live database: `/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/factory.db`
- Before/after physical SHA-256: `5b9400c90a45d4ee82b9b6d98adfd53c998d9519be33e802a4e44fcb5340461c`
- Before/after size: `25280512`
- Before/after mtime: `2026-08-31 21:51:35.517134579 -0500`
- Before/after inode: `1290305881`
- Before/after logical dump SHA-256: `e44f478da1cf1eb84d2f9d23ea2778a23ed26a36aca4b255b32134a67e7f61ba`
- Before/after event count: `5961`
- Before/after state: paused, zero active jobs, zero active workers, quick check `ok`, zero FK violations.
- `cmp live-before.txt live-after.txt` passed byte-for-byte.

The consistent backup command was:

```bash
sqlite3 -readonly /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/factory.db \
  ".backup '/projects/se/pj34000401_refsys/users/yuali01/learn/.integrated-tip-rehearsal.oPJyoxLp/copied-live-pristine.db'"
```

The backup's physical SHA-256 is
`78e058de1338f1389e292caa136088482bbca2fbdf740da983892d61f747d8ec`; its logical dump digest exactly
matches the live digest above. `copied-live-pristine.db` was made mode `0444` before the working copy was
used.

## Explicit copy-only relocation fixture

The live snapshot has one nonterminal attempted legacy BYOX job whose persisted workspace names the
live warehouse. The reachability predicate returned `true` against the actual live warehouse and
`false` against the isolated rehearsal warehouse. This is expected path binding, not corrupt live
state. Evidence: `workspace-reachability-before-rebase.json`.

Only in the disposable copy, exactly one `workspace` cell was rebased before cutover:

- Job: `job_byox_build_v1_22a4d41b09ee36d12fb994cbb5cb997d`
- Old: `/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_build_v1_22a4d41b09ee36d12fb994cbb5cb997d/attempt-001`
- New: `/projects/se/pj34000401_refsys/users/yuali01/learn/.integrated-tip-rehearsal.oPJyoxLp/warehouse/workspaces/job_byox_build_v1_22a4d41b09ee36d12fb994cbb5cb997d/attempt-001`
- Row digest before: `f8b70aac5d316d5f18a6181c6562be1e721efbc7b21da040cf6764d807632123`
- Row digest after: `b31ea8244de1c5aa7f0d24152a35391886de6f3c8bcc9efeb7cfc4d0e5dc48c5`
- Changed rows: `1`; changed columns: `workspace`; reachability after rebase: `true`.

Evidence: `copy-only-workspace-rebase.json`. The intentionally retained first failed run in
`seed-all-first.stderr` demonstrates the isolated-path fail-closed behavior.

## Commands and results

The isolated config pins `gpt-5.6-sol`, `ultra`, and the ARM endpoint
`https://openai-api-proxy.geo.arm.com/api/providers/openai/v1`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m learnfactory \
  --config /projects/se/pj34000401_refsys/users/yuali01/learn/.integrated-tip-rehearsal.oPJyoxLp/config.toml init
```

Applied migrations: `015_scheduler_io_indexes.sql`, `018_scheduler_claim_cursor.sql`,
`019_byox_baseline_snapshots.sql`, and `020_job_retry_allowance.sql`. Evidence: `init-final.json`.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m learnfactory \
  --config /projects/se/pj34000401_refsys/users/yuali01/learn/.integrated-tip-rehearsal.oPJyoxLp/config.toml seed-all
```

First convergent seed:

- Created jobs: `882` (`718` BYOX S2 plus `164` CSDIY v2 student/examiner jobs).
- BYOX: `359/359` catalog entries covered; `359` builders and `359` reviewers.
- CSDIY: `82/82` catalog entries covered; all `246` old cohort rows retained and all current
  preparation/student/examiner roles present for `82` courses; target learner coverage `82/82`.
- Legacy BYOX: `723` total; `655` exact nonterminal rows retired with `655` unique cancellation events;
  all `68` preexisting terminal rows preserved.
- Legacy CSDIY examiner reconciliation: `79` unsafe queued rows cancelled; terminal history retained.
- The command did not execute jobs.

Raw output: `seed-all-final-first.json`. Independent assertions:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 \
  /projects/se/pj34000401_refsys/users/yuali01/learn/.integrated-tip-rehearsal.oPJyoxLp/verify_integrated_cutover.py
```

Verification result (`verification-first.json`):

- `359` immutable baselines.
- `718` bindings, all reloaded with `load_verified_binding`.
- Binding roles exactly `359` builder and `359` reviewer.
- Builder profile exactly `359 reference_builder / gpt-5.6-sol / ultra`.
- Reviewer profile exactly `359 examiner / gpt-5.6-sol / ultra`.
- `82` active courses, `246` current cohort graph jobs, target learner on all `82` courses.
- Three durable learner identities retained.
- Quick check `ok`, zero FK violations, zero active jobs/workers, paused `true`.

## Strict repeat no-op

The same `seed-all` command was run again. It returned:

- `created_jobs=0`
- BYOX `created_jobs=0`, builders `0`, reviewers `0`
- CSDIY `created_jobs=0`, invalidations `0`
- legacy examiner cancellations/requests `0/0`
- `promoted_ready=0`
- `execution_started=false`

Before and after the repeat:

- Physical DB SHA-256: `fa760e23543930393df4384f64238bd82f09870a14a3c2fa00de84c9372b8409`
- Logical dump SHA-256: `59990ac7406804fc24eb797b2bbe555c9af5be09be3fb34961f6a81fbbad3979`
- Size: `40431616`
- Mtime: `2026-08-31 22:01:01.567060203 -0500`
- Events/max event: `9162/9162`

`cmp repeat-before.txt repeat-after.txt` and
`cmp verification-first.json verification-after-repeat.json` both passed byte-for-byte.

## Decision

GO for the exact integrated commit. The real live warehouse path satisfies the sole attempted legacy
runtime binding, the copied cutover converges after the explicit rehearsal-only path rebase, every
required catalog/cohort/baseline/binding invariant passes, and a second seed is a physical and logical
no-op. The live database remained physically and logically unchanged throughout this rehearsal.
