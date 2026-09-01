# Operations

Bootstrap from an empty warehouse in this order:

```bash
PYTHONPATH=src python3 -m learnfactory init
PYTHONPATH=src python3 -m learnfactory ingest ../cs-self-learning ../build-your-own-x
PYTHONPATH=src python3 -m learnfactory run --until-idle
PYTHONPATH=src python3 -m learnfactory seed-all
PYTHONPATH=src python3 -m learnfactory status
PYTHONPATH=src python3 -m learnfactory run --until-idle
PYTHONPATH=src python3 -m learnfactory jobs --state FAILED
PYTHONPATH=src python3 -m learnfactory inspect JOB_ID
```

The first `run` validates and atomically publishes commit-pinned normalized catalogs. `seed-all` then
creates the complete durable, backend-gated CSDIY/BYOX graph without executing it; running it before
catalog publication fails rather than creating jobs with missing or mutable provenance. Start with the
single capability gate and inspect its evidence before increasing bounded throughput. The authoritative
gate marker is validated and archived from a controller-installed fresh-inode snapshot, so retained Codex
handles cannot alter the bytes that unlock dependencies. The authoritative bootstrap is therefore:

```text
init -> ingest -> run -> seed-all -> bounded run
```

Operate bounded work:

```bash
PYTHONPATH=src python3 -m learnfactory run --until-idle
PYTHONPATH=src python3 -m learnfactory run --max-jobs 10
PYTHONPATH=src python3 -m learnfactory pause
PYTHONPATH=src python3 -m learnfactory resume
PYTHONPATH=src python3 -m learnfactory retry JOB_ID
```

The live configuration permits 12 concurrent claims, subject to per-type ceilings: five
`reference_builder`, two `course_manager`, two `student`, and three `examiner` jobs. Other roles retain
their lower configured limits. A continuous `run --until-idle` controller is active at this checkpoint
and fills only eligible slots. The earlier `run --max-jobs 3` was a three-dispatch safety probe;
`--max-jobs` caps total launches by that invocation and should not be confused with `max_concurrency`.
Starting another controller is safe with respect to duplicate claims and shared limits, but is normally
unnecessary while the existing controller is healthy.

`pause` commits the durable flag and audit event together. A claim that linearizes after that commit
cannot acquire ownership, including after a slow catalog refill or between two capacity-filling
launches. Jobs already in `CLAIMED` or `RUNNING` are deliberately not cancelled; use the explicit
cancel command when termination is intended. `resume` atomically clears the fence and records its event.

The rollback-journal database lives on NFS. Keep
`factory.database_busy_timeout_seconds + factory.heartbeat_seconds < factory.lease_seconds`; invalid
configurations fail at startup. The default configuration is 20 + 5 < 30 seconds. Worker stderr uses
JSON records whose `component` is `worker-heartbeat`; alert on `HEARTBEAT_LEASE_AT_RISK`,
`HEARTBEAT_FATAL_DATABASE_ERROR`, and repeated `HEARTBEAT_DATABASE_CONTENTION`. A later
`HEARTBEAT_RECOVERED` closes a transient contention episode.

Heartbeat/watchdog lease loss is a retryable local interruption, never evidence that an artifact may be
published. The worker checks it after handling, validation, archive preparation, and once more after
quiescing and joining heartbeat plus watchdog. If SIGTERM is observed before that final check, the job is
interrupted for retry with exit 143. The completed final check is the local stop linearization point, so a
later SIGTERM allows the already-started publication to finish. Use durable `cancel` when publication must
be transactionally excluded: `cancel_requested` is rechecked by the SQLite success transaction even after
the local linearization point.

An in-flight heartbeat is first validated against the previously observed monotonic lease deadline and
only then allowed to honor publication quiescence. A renewal returned after that deadline sets local
cancellation even if `request_stop()` arrived while SQLite was blocked. Supervisor signal delivery and
local failure classification share the publication gate; classification rechecks the supervisor cause
after observing shared cancellation, so a delivered SIGTERM produces interrupt/exit 143 rather than a
local lease-failure/exit 6.

Publication callbacks are controller code and must declare an orchestrator-selected
`PublicationScope`. Do not place model-generated or otherwise untrusted Python in this hook. The facade
and authorizer reject transaction control, DDL, pragmas, attachment, extensions, control-plane writes,
and cross-domain writes, but they are defense against API/SQL misuse rather than a Python sandbox. A
denial remains sticky if callback code catches it; the job records non-retryable `publication_failure`
instead of being misreported as a dependency block. Facade capabilities expire when the callback exits.
Do not retain or hand them to background work; such operations are rejected, and revocation is serialized
with any operation already in flight so authorizer restoration has no check/use window. Publication uses a
fresh controller-owned connection, refuses a tracked existing authorizer, and leaves that callback
untouched; remove it before publication rather than trying to compose it. During publication, tracked
replacement is sticky-denied and direct base-descriptor replacement between operations is repaired before
the next facade SQL. CPython exposes no authorizer getter, so a callback installed through the unbound base
descriptor before activation is neither detectable nor restorable. Code holding the raw connection/base
descriptor is trusted controller code, is outside this API isolation contract, and must never race
publication.

### Combined migration integration order

This scheduler branch intentionally contains migration `018_scheduler_claim_cursor.sql` and does not
duplicate migrations 016 or 017 from the prerequisite integration branches. When combining the work,
integrate the complete 016 and 017 commits first, then this branch, and only then run `learnfactory init`
so the authoritative ledger applies 016, 017, and 018 in order. Do not copy, renumber, or independently
edit already-applied migration files; reconcile the combined history before any environment applies 018.

Reproduce the scheduler query-footprint benchmark without touching the operated database:

```bash
PYTHONPATH=src python3 scripts/measure_scheduler_io.py \
  --jobs 5000 --payload-bytes 4096 --eligible-offset 129
```

On 2026-08-31 with Python 3.11.5 and SQLite 3.26.0, the exact production claim-selection helper found
the first eligible row after 129 fenced rows in 397 SQLite VM steps. Independently released bounded
pages used 5,123 steps for 2,500 all-fenced rows and 10,240 for 5,000: a 1.999x ratio and 2.048 steps/job.
The deliberately adversarial all-equal-priority fixture produced the same 5,123/10,240 linear result,
which verifies the persisted row-value cursor rather than only the common distinct-priority case. The
dependency-aware predicate was measured separately with every READY child bound to a cancelled parent:
2,500/5,000 rows required 2,506/5,006 steps, a 1.998x ratio, selected no job, and never opened a writer.
This exercises the exact missing/non-successful-prerequisite filter rather than inferring its cost from
dependency-free rows. The exact production progression and one-pass kickoff-grouping helpers used 500
and 254 steps respectively
with 250 scoped IDs among 5,000 jobs. The former whole-READY materialization returned 5,000 rows and
20,556,450 payload bytes. Per-opcode progress hooks distort timing, so the JSON labels those elapsed
values explicitly. Fixtures use unique system temporary directories and are removed; no operated
database is opened.

Heartbeat lock tests use a real rollback-journal database with one connection blocking
`BEGIN IMMEDIATE` and another retaining the SHARED lock needed to block `COMMIT`. They verify cancellation
before the prior durable expiry both with the production dynamic timeout and with a deliberately
uncapped heartbeat that commits late. The late-commit case also starts a final publication quiesce and
verifies it waits for heartbeat/watchdog termination and observes cancellation. Journal normalization
tests synchronize six spawned processes on a current WAL database and verify all converge to `DELETE`
with an intact migration ledger.

Mass-seeded BYOX/CSDIY jobs are fenced at execution, not merely by the current global defaults. Older
queued rows may legitimately lack `required_backend`; do not rewrite them to add it. The launch seam
still requires `exec`, `factory-isolated`, `gpt-5.6-sol`, and `ultra` using the durable job model fields.
It also requires provider `arm`, base URL
`https://openai-api-proxy.geo.arm.com/api/providers/openai/v1`, authentication enabled, and WebSockets
disabled in the effective settings. A mismatch or a conflicting explicit policy becomes
`blocked_backend_configuration` before Codex is spawned. Newly seeded catalog and course-progression
rows include the explicit payload policy for inspection.

Production also sets `factory.allow_host_command_validators = false`. The scheduler then leaves any
READY job with a `command` validator or command-mode `review_acceptance` untouched, including malformed
validator envelopes, and continues scanning for structural jobs. `status` prints the current held count
as `claim fence`; a held job has not failed and has not consumed an attempt. Do not enable this switch in
production merely to drain the queue. It is reserved for isolated tests until the command sandbox earns
independent release approval. The backend-capability bootstrap gate uses an in-process exact SHA-256
check and remains claimable with the fence active; a fresh database must never require enabling host
commands to unlock its catalog graph.

`SIGINT` and `SIGTERM` stop new claims and give child workers a grace period. A new scheduler first
checks published v2 artifact integrity, promotes satisfied dependencies, and recovers expired leases.
Structured worker stdout/stderr and Codex JSONL are retained below `warehouse/logs/`.

Each newly started run writes `RUN_PROVENANCE.json` beside those logs and stores the same JSON plus its
combined SHA-256 in `job_runs`. Inspect it without reading raw SQLite JSON manually:

```bash
PYTHONPATH=src python3 -m learnfactory inspect JOB_ID
```

The `runs[].reproducibility` object contains separate code/configuration/policy/invocation digests,
repository commit and dirty/untracked path status, the allowlisted effective configuration, and a
secret-free argv manifest. `prompt.sha256` represents the actual leaf-worker envelope plus job prompt,
not merely the raw payload prompt. A `PARTIAL`, `RACED`, `UNAVAILABLE`, or `CAPTURE_FAILED` status is
evidence of a limitation and must not be interpreted as a complete byte snapshot. Historical runs with
`{}` and a null digest predate this facility; do not backfill them speculatively.

The scheduler's drain is exception-safe: an unexpected controller-loop error still enters cleanup,
waits for active children for the configured grace interval, escalates process groups when necessary,
reaps them, and finalizes bounded redacted logs. The original controller error is preserved; a cleanup
error is attached to it rather than replacing it. This protects ordinary errors and signals, not a
hard kill of the scheduler or worker process.

Workers terminate their subprocess groups during ordinary cancellation, timeout,
and graceful shutdown. A host-level `SIGKILL` of the worker itself can bypass that
cleanup and leave an independently sessioned Codex or validator descendant alive.
After a hard kill, audit the host process table using the recorded worker/job and workspace context
before retrying. Descendant PIDs are not durably inventoried, so the factory cannot prove from SQLite
alone that none survived. A cgroup, subreaper, or parent-death-signal launcher is planned before
hostile multi-tenant use.

Durable artifacts and failed educational attempts are never garbage-collected implicitly. Scratch
workspaces currently require deliberate operator review and removal; there is no cleanup CLI yet.
Only terminal-job workspaces should be considered eligible.

## Codex provider and authentication

The verified standalone route is:

```text
provider:             arm
base URL:             https://openai-api-proxy.geo.arm.com/api/providers/openai/v1
wire API:             Responses
WebSockets:           disabled
model:                gpt-5.6-sol
reasoning effort:     ultra
authentication:       reused from Codex's supported auth store
```

The capability job `job_codex_backend_gate_v1` completed through this route and its exact output passed
external validation. The factory configuration contains routing metadata only. Never place a token,
cookie, API key, or copied auth file in TOML, a job payload, a prompt, SQLite, a generated repository, or
operator documentation.

Inspect backend and historical blockers with:

```bash
PYTHONPATH=src python3 -m learnfactory jobs --state BLOCKED
PYTHONPATH=src python3 -m learnfactory inspect JOB_ID
```

Some earlier jobs remain durably `blocked_authentication` from the old default endpoint. The successful
gate does not erase their attempt history or silently retry them. Inspect each job, then manually retry
only work that should be resumed. An examiner already marked `blocked_dependency` becomes retryable only
after its student dependency succeeds:

```bash
PYTHONPATH=src python3 -m learnfactory retry STUDENT_JOB_ID
PYTHONPATH=src python3 -m learnfactory run --until-idle
PYTHONPATH=src python3 -m learnfactory retry EXAMINER_JOB_ID
PYTHONPATH=src python3 -m learnfactory run --until-idle
```

Manual retry preserves attempt history and grants one additional attempt. A successful capability gate
proves this bounded invocation path, not unlimited capacity; retain configured concurrency limits and
respect service throttling.

## Codex worker permission profile

New model jobs use `factory-isolated`; the backend no longer passes the legacy `--sandbox` option. Each
invocation ignores operator config and rules, uses strict configuration, denies the filesystem root,
writes only its workspace, reads only Codex's minimal runtime plus the exact configured Python toolchain,
and hides `CODEX_HOME` including its authentication file from job tools. Tool network is disabled, no
operator environment is inherited, and hosted/web, MCP, browser/computer-use, plugin, hook, skill, and
native subagent surfaces are disabled. The Codex parent still reaches the configured ARM model endpoint
using its supported authentication path; that does not give the model's shell or other tools network or
auth-file access.

The installed Linux permission-profile runner is beta. The host integration probe demonstrates denial
of a sibling file, auth storage, inherited environment, and network sockets, but is not a proof of
hostile multi-tenant isolation. `/proc` is requested as denied, while bounded final-message capture
necessarily uses an inherited `/proc/self/fd/...` descriptor; do not infer that every possible process
metadata path has been formally excluded. Use a container or VM managed outside the worker for hostile
code or secrets.

## Current scale-out checkpoint

The active graph covers 359 BYOX entries with one selected builder and one independent reviewer apiece,
and 82 CSDIY courses with manager, persistent target-student kickoff, and independent examiner jobs.
This is scheduling coverage, not educational completion. The generic BYOX builder
`job_byox_build_v1_bb68cd7e2c05f8b000f3e7bfd2e54a32` is currently on attempt two after its first
candidate failed external validation for containing a forbidden root `.git`; the failed candidate was
not published. Two v1 BYOX reviewer jobs completed under the former output-only contract. Their
`SUCCEEDED` state means their review files were archived, not that either candidate was accepted.
`seed-all` idempotently creates provenance-linked v2 remediation reviewers with the deterministic
verdict contract.

Interpret BYOX review results as follows:

- `PASS`: archive an advisory positive review; it does not mint `REVIEWED` or accept the candidate.
- `REVISE` or `FAIL`: archive the review as useful negative evidence, but do not mint `REVIEWED` or
  count the pair as accepted.
- Missing, legacy, conflicting, or ambiguous verdict evidence: fail closed for acceptance even if the
  reviewer process exited successfully.

Candidate acceptance is a separate `review_acceptance` check. It is closed by default. Only configured
command mode, with a real captured command/exit/output record and exact checksum-bound artifacts, may
mint `REVIEWED`; reporting rejects a reviewer verdict presented as acceptance evidence.

## Bounded CSDIY continuation

Refill at most one kickoff revision or next normalized-resource batch per selected course:

```bash
PYTHONPATH=src python3 -m learnfactory seed-course-next --max-courses 10
PYTHONPATH=src python3 -m learnfactory run --until-idle
PYTHONPATH=src python3 -m learnfactory seed-course-next --course-id COURSE_ID
```

Each refill creates or repairs one materializer/student/examiner DAG per eligible course and does not
start it. A kickoff `REVISE` or `FAIL` creates a fresh, independent, checksum-bound revision pair up to
`factory.course_revision_limit`; a passing revision can then unlock the ordinary bounded unit graph.
Re-running while an ordinal is active is a safe no-op, partial graphs are repaired, and exhaustion is
reported as `BLOCKED_KICKOFF_REVISION_LIMIT_EXHAUSTED` with `course_completion: NOT_CLAIMED`. Stale or
conflicting provenance, missing verified artifacts, unresolved dependencies, and revision forks fail
closed. Conflicting same-attempt examiner rows are never resolved by timestamp; their result, evaluator,
rubric, and exact student/examiner attempt bindings must be unambiguous. `NORMALIZED_RECORDS_EXHAUSTED`
means only that the local normalized catalog records have bounded
examiner evidence; it never means the official course, unavailable assignments, exams, or a transfer
evaluation were completed.

## Artifact integrity incidents

Startup reconciliation is fail-closed for published `tree-sha256-v2` records. If bytes are missing,
changed, symlinked, special, or outside the configured artifact store, the record becomes
`LEGACY_UNVERIFIED` and gains `PARTIAL` evidence plus an integrity-quarantine event. The bytes are not
automatically repaired or deleted. Inspect the artifact and job evidence before rebuilding or retrying:

```bash
PYTHONPATH=src python3 -m learnfactory artifacts
PYTHONPATH=src python3 -m learnfactory inspect JOB_ID
PYTHONPATH=src python3 -m learnfactory report
```

## Archived BYOX code-presence revalidation

Re-evaluate previously published BYOX challenge packs in bounded batches after a structural gate
change:

```bash
PYTHONPATH=src python3 -m learnfactory revalidate-byox-code --max-artifacts 100
PYTHONPATH=src python3 -m learnfactory revalidate-byox-code --artifact-id ARTIFACT_ID
```

The default scan skips artifacts that already have an observation for the exact current policy digest,
so repeated batches advance without rewriting history. An explicit artifact ID replays that artifact;
an identical observation resolves to its existing deterministic audit row. A changed observation is
appended and the artifact/policy binding becomes `CONFLICT`. The command copies the complete archive
through no-follow file descriptors into a random private mode-`0700` factory scratch directory. It
requires a tree checksum derived from the copy's immutable metadata/content-hash manifest and copied
tree to equal the stored checksum. The narrower gate evaluates that in-memory manifest—not the mutable
path. Source rechecks detect drift, but the stored-checksum-identical detached copy is the authority;
the command does not claim a sequence of live-tree scans is atomic. Checksum
drift, multiple artifacts for one job attempt, path aliases across any artifact type, symlinks, special
files, malformed bindings, and contradictory final-policy controller evidence all fail closed.

One invocation selects at most 100 artifacts by default and additionally accepts at most 512 MiB of
aggregate bytes actually read or 15 minutes of wall time. Every source hash, source-to-snapshot copy,
and snapshot hash is charged, including partial reads from trees later rejected. A successful replay
currently reads ordinary file content six times, so raise the byte override deliberately for larger
archives. The programmatic maintenance API caps overrides at
1,000 artifacts, 2 GiB, and one hour. Root components, queued directories, and files are opened relative
to held no-follow directory descriptors, so a directory-to-symlink replacement cannot redirect hashing
outside the archive. If an aggregate budget is reached, output includes `stopped_reason` and
`stopped_artifact_id`; the interrupted artifact receives no audit row and remains eligible for the next
invocation. This operational stop is not evidence that the artifact failed its structural gate.
Wall expiry is checked again inside the SQLite write transaction immediately before reuse or insertion;
expiry and primary byte exhaustion cannot be converted into a durable FAIL by delayed append or scratch
cleanup failure.

Rows live in the append-only `byox_code_presence_audits` table and bind the exact artifact ID, owner job,
physical attempt, stored and observed checksums, job-payload digest, policy digest, and policy-spec digest.
They never modify `artifacts`, `artifact_validation_labels`, `validations`, job payloads/states, or archive
files. `PASS` means only that required code-shaped files are structurally present in the expected trees;
it never adds `BUILDS`, `TESTED`, or any other artifact label. Build and test claims still require
independent executable validator evidence.

## BYOX validation cutover incidents

A BYOX builder is validated only after the controller replaces its worker-visible attempt tree with
fresh inodes. Ordinary packs retain the complete safe copy. For remediation builders,
the controller copies only the declared artifact projection and protected inputs;
undeclared roots are not copied into that snapshot, and their bounded hashes remain in the cutover
quarantine record. The retired worker tree is temporary forensic input and is discarded after cutover,
while the cutover record travels with a successful artifact.

If a repair fails with `unsafe_archive_projection`, `repair_snapshot_changed`,
`repair_cutover_invalid`, or a staged-input binding error, do not manually copy files into the attempt
directory or edit its records. Keep the failed attempt immutable, inspect its job events and logs, correct
the deterministic capture contract or worker prompt as appropriate, then issue a normal retry. A retry
gets a fresh attempt and workspace; earlier attempt evidence remains intact.
