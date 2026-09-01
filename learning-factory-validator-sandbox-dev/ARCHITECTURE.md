# Architecture

```text
local Git objects -> pinned source preparation -------------------+
                                                                 |
SQLite control plane -> scheduler/leases -> isolated worker ------+-> candidate files
                                              |                    -> independent validators
                                              |-> deterministic handler
                                              `-> standalone CodexBackend

validated candidate -> same-filesystem fsynced staging + rename
                    -> fenced SQLite publication + job success
                    -> checksummed artifact record
```

One Python process is sufficient to schedule work, but all ownership is persisted. Claims use a
SQLite write transaction, dependencies are normalized in `job_dependencies`, and a database trigger
enforces the state machine. Each claim increments an attempt number and gets a lease. The worker
harness registers its PID, transitions the claim to running, heartbeats independently, executes one
handler, runs configured validators, hashes promoted output, then performs the terminal transition.
Artifact metadata records the factory Git commit and whether tracked generator/control-plane files
were clean at generation time, alongside source commits, job/run IDs, commands, and validation evidence.
At worker start, migration-backed `job_runs` fields also capture a versioned reproducibility fingerprint
and human-readable JSON record. The combined digest binds separate code, configuration, job-policy, and
invocation digests. Code hashing covers tracked and non-ignored untracked execution paths with explicit
bounds and race/omission status; configuration copies only allowlisted parsed values. The invocation
manifest shares its argv and effective leaf-worker prompt-envelope builders with the actual backend, so
model, reasoning, permission profile, toolchain roots, effective-prompt SHA, and secret-free CLI flags
cannot drift silently from execution.
The configured standalone backend is `codex exec --json` using provider `arm` at
`https://openai-api-proxy.geo.arm.com/api/providers/openai/v1`, the Responses wire API, and WebSockets
disabled. Its default quality profile is `gpt-5.6-sol` with `ultra` reasoning. The provider asks Codex
to reuse its supported authentication; credentials are not copied into factory configuration or job
state. Per-job quality overrides remain possible and effective values are recorded in `job_runs`.

New exec-backend jobs are launched with Codex's named `factory-isolated` permission profile, not
`--sandbox`. Invocation is fail-closed (`--ignore-user-config`, `--ignore-rules`, `--strict-config`):
the profile denies `:root`, reads only `:minimal`, the resolved Codex executable, and exact configured
toolchain roots, writes only the current workspace, disables job-tool network access, inherits no shell
environment, hides `CODEX_HOME`, and disables web/hosted, MCP, browser/computer-use, plugin, skill,
hook, and native subagent surfaces. The model transport to the ARM provider remains available to the
Codex parent; the model's tools do not receive general network access or the authentication file.

The reproducibility JSON is inserted in the same transaction as the `job_runs` row and is also written
mode `0600` as `warehouse/logs/<job>/attempt-NNN/RUN_PROVENANCE.json`. A
`RUN_REPRODUCIBILITY_CAPTURED` event exposes its fingerprint to operators, and successful artifacts link
the same digest. Historical rows predating the migration remain explicitly blank rather than receiving
fabricated backfill evidence.

The scheduler may die without erasing history. Live workers continue heartbeating; expired claims are
converted to retry-wait or failed according to their persisted attempt limit. Global and worker-type
limits count claims in SQLite, so two scheduler processes still share capacity. The operated ceiling is
12 concurrent claims: five reference builders, two course managers, two students, and three examiners
can fill the principal workload slots, while other worker types retain their own configured caps. A
continuous `run --until-idle` controller is active and keeps filling eligible slots until the durable
graph becomes idle. Scheduler cleanup is
in a `finally` path: normal stops and unexpected controller exceptions drain or terminate active
children, reap them, and persist bounded redacted stdout/stderr before supervision is relinquished.

## Main components

- `db.py`: migrations, connections, transactions, event append.
- `jobs.py`: state machine API, dependency promotion, atomic claims, leases, retry policy.
- `scheduler.py`: bounded dispatch, child supervision, recovery, graceful shutdown.
- `worker.py`: deterministic worker harness and handler dispatch.
- `backends/`: Codex abstraction plus exec and fake implementations.
- `sources/`: repository adapters that emit normalized course and project records.
- `workspace.py`: attempt allocation, safe student views, artifact hashing/promotion.
- `validation.py`: required-path, JSON-schema subset, command, and checksum validators.
- `validator_sandbox.py`: quarantined, fail-closed local command primitive. It requires proven
  kernel memory/pids cgroup ceilings, an isolated namespace stack, an explicit minimal runtime, and
  independent signal evidence; it is not wired into artifact promotion.
- `reporting.py`: human and machine operator checkpoints and artifact catalog.

## Backend gate and catalog-scale graph

Mass model work depends on one small, externally validated Codex capability job. A failed gate prevents
hundreds of children from independently discovering the same routing or authentication fault. The
verified gate currently fronts a graph covering all 359 active BYOX entries and 82 active CSDIY courses.
Each BYOX entry has a selected builder and separate reviewer; each course has a bounded preparation,
persistent target-student kickoff, and separate examiner. These are durable planned relationships, not
claims that the projects or courses are complete.

The generic Docker-in-Bash builder is retrying after its first candidate failed the external
forbidden-path validator for creating a root `.git`; that candidate was not published. Two earlier BYOX
review jobs reached `SUCCEEDED` before the deterministic verdict contract existed. They prove only that
review artifacts were generated, not that their candidates were accepted. The v2 remediation creates
new, provenance-linked reviewer jobs rather than mutating attempted v1 history.

Review verdict validation deliberately treats `PASS`, `REVISE`, and `FAIL` as structurally valid review
outcomes. All are archived, but even an exact reviewer `PASS` is advisory and cannot emit `REVIEWED`.
Acceptance is a separate `review_acceptance` validator; its default mode is closed, and only a configured
command-mode check with captured command, exit status, output, evidence, and exact artifact bindings may
emit `REVIEWED`. Reporting accepts a pair only when that independent acceptance record and the current
checksum-verified builder/reviewer artifacts agree. Ambiguous, legacy, or review-only evidence fails closed.

`seed-course-next` is a deterministic, bounded graph refiller. For each selected eligible course it
materializes at most one normalized resource record into a three-job materializer/student/examiner DAG.
It requires a current checksum-verified preparation artifact and a control-plane-bound PASS from the
kickoff or prior examiner, repairs partially persisted DAGs idempotently, and snapshots provenance plus
the external learner model. Every emitted manifest says `course_completion: NOT_CLAIMED`; normalized
catalog-record exhaustion is not evidence that lectures, assignments, exams, transfer work, or the
course were completed.

## Source snapshot lifecycle

Adapters inspect tracked Git objects at a pinned commit, not mutable working-tree bytes. Ingestion
prepares a DB-free normalized batch in the job workspace and checks that the observed commit still
matches the commit recorded when the job was enqueued. A canonical repository path has exactly one
active source snapshot. Ingesting a newer commit deactivates the previous snapshot and records its
successor without deleting the historical source or its normalized rows. Catalog synthesis, seeding,
planning, reporting, and artifact generators select only active snapshots.

Scheduled ingestion does not mutate catalog tables during preparation. After external validation,
the source activation callback, artifact row and labels, and fenced `RUNNING -> SUCCEEDED` transition
commit in one SQLite transaction. Cancellation, an expired/replaced lease, or any publication error
rolls that transaction back, so an attempt cannot publish source rows without publishing its validated
artifact and succeeding under its current lease.

## Artifact durability and integrity

Artifact bytes cross a filesystem boundary before the SQLite publication transaction:

1. Copy the validated workspace into a temporary `.staging` directory beside the final destination.
2. `fsync` every regular file and directory, compute the framed `tree-sha256-v2` checksum, rename
   within that same directory/filesystem, and `fsync` the destination and parent chain.
3. Recheck the tree checksum, lease fence, cancellation flag, dependency state, and validator evidence
   while publishing the artifact row and terminal job state in one SQLite transaction.

SQLite and the filesystem cannot share one atomic transaction. A publication rollback normally
deletes the prepared tree; a crash can still leave an unreferenced directory. Conversely, every
scheduler startup recomputes each published `VERIFIED_V2` artifact checksum. Missing, changed,
symlinked, special-file, or out-of-store trees are logically quarantined as `LEGACY_UNVERIFIED` plus
`PARTIAL`, with an `ARTIFACT_INTEGRITY_QUARANTINED` event. Reconciliation neither repairs nor silently
deletes the bytes. Legacy `tree-sha256-v1` records are preserved but are non-stageable dependency
evidence because their old unframed tree hash is structurally ambiguous.

## Trust boundaries

Source snapshots are never edited. Candidate output and grader material occupy different directories.
Copied student views and read-only, checksum-bound dependency staging remain the first structural
boundary; new Codex invocations also use the tested `factory-isolated` permission profile described
above. A host probe verifies that a job can read its workspace but cannot read a sibling sealed file or
the Codex auth file, inherit an operator sentinel, or create a network socket.

The Codex Linux permission-profile runner is beta, all host processes still share one Unix identity,
and this is not advertised as a formally verified hostile multi-tenant boundary. In particular, the
configuration requests `/proc` denial but the backend necessarily passes its bounded final-message
stream through an inherited `/proc/self/fd/...` descriptor; process-filesystem mediation has nuanced
exceptions and the test does not prove every `/proc` path inaccessible. Use a separately administered
container/VM boundary for hostile code or secrets. Hidden-test paths are passed only to deterministic
validators in workflows that make that guarantee.

Workers, Codex commands, and validators use process sessions so routine timeout, cancellation, and
graceful shutdown can terminate their process groups. A hard `SIGKILL` delivered to the supervising
worker bypasses its cleanup; independently sessioned descendants are not yet owned by a cgroup,
subreaper, or parent-death signal and can survive until an operator audits and terminates them.
