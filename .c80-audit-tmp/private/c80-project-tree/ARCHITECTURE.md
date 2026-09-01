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
handler, applies the host-command fence to the handler's actual validator envelope, runs configured
structural validators, hashes promoted output, then performs the terminal transition.
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
toolchain roots, disables job-tool network access, inherits no shell environment, hides `CODEX_HOME`,
and disables web/hosted, MCP, browser/computer-use, plugin, skill, hook, and native subagent surfaces.
A canonical `SandboxRuleManifest` adds the exact per-job filesystem rules and is shared by provenance
capture and runtime rendering. Ordinary jobs may write their workspace while more-specific staged-input
binds remain read-only. Every CSDIY examiner workspace is empty and root-denied; its manifest has no
inner filesystem rules and disables all command/execution/artifact capabilities. The model transport to the
ARM provider remains available to the Codex parent; the model's tools do not receive general network
access or the authentication file.

The final model response travels through a randomized mode-private file beneath the controller-only
`warehouse/.controller-result-channels/<job-hash>/attempt-NNN/` tree, not the attempt log directory, an
inherited file descriptor, or an inner writable rule. The controller hard-links that inode to the sole,
fixed-name entry in `logs/<job>/attempt-NNN/.codex-controller-launch/`, opens the alias read-only and
no-follow, and passes the outer CLI an ephemeral `/proc/<controller-pid>/fd/<fd>` output pathname. The
descriptor stays in the controller and is not inherited by Codex. The installed permission runner
verifies that an inner tool given that exact pathname cannot open, read, write, or truncate it, while the
trusted outer CLI can open it for `--output-last-message`. No-tools launches use a parent-held procfd
name for the fixed-alias directory as cwd; tool-enabled launches use the workspace. Neither form exposes
a randomized name. Before any mutation, the controller walks every absolute
ancestor one component at a time through `O_DIRECTORY|O_NOFOLLOW` descriptors, creates private
components with descriptor-relative operations, and captures directory and file inode/type/mode/owner/
link bindings. The fixed transport-base descriptor remains held while nonce-bearing descendant
descriptors are parked during Codex execution, then those descendants are reopened only from that base
and only when every captured binding still agrees. The controller pins the alias/channel inode identity
and exact link count, then removes the alias by its retained directory descriptor after Codex exits. The backend
terminates the original process group, uses Linux child-subreaper reconciliation to terminate detached
descendants, and validates through held no-follow directory descriptors that each namespace has exactly
the expected bounded shape and the result is a fresh regular single-link file before reading it. The
channel, nonce directory, and empty invocation roots are removed with `unlinkat`/`rmdirat`-style
descriptor-relative calls; absolute `Path` values are diagnostic metadata after validation, never
mutation authorities. An ancestor replacement or uncertain binding preserves the captured evidence and
cannot redirect creation or cleanup into the replacement tree. POSIX has no inode-conditional
`unlinkat`/`rmdirat`, so the final binding-check-to-removal interval assumes these mode-`0700` invocation
directories are quiescent after the trusted CLI and its descendants are reaped; a hostile same-UID
process rewriting entries inside an already-held directory in that interval is outside this boundary.
Provenance binds the v3 result-channel class and the same sandbox manifest without
storing the private runtime path, nonce, numeric PID/FD pathname, or a digest derived from them; retained
numeric procfd text is replaced by a fixed marker. The bounded redacted final
message remains ordinary retained output, not provenance content.

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
- `result_channel.py`: canonical controller-private transport and fixed launch-alias topology.
- `sources/`: repository adapters that emit normalized course and project records.
- `workspace.py`: attempt allocation, safe student views, artifact hashing/promotion.
- `validation.py`: required-path, JSON-schema subset, command, and checksum validators.
- `backend_policy.py`: launch-time recognition and exact runtime/ARM-route fencing for catalog-scale Codex work.
- `byox_gate_backfill.py`: bounded, append-only archive replay; a private no-follow copy yields an
  immutable metadata/content-hash manifest whose derived tree checksum is bound to the stored artifact,
  and the pure gate evaluates that manifest rather than any mutable path. Root components, queued
  directories, and files are reopened only beneath held no-follow directory descriptors.
- `reporting.py`: human and machine operator checkpoints and artifact catalog.

## Backend gate and catalog-scale graph

Mass model work depends on one small, externally validated Codex capability job. A failed gate prevents
hundreds of children from independently discovering the same routing or authentication fault. The
verified gate currently fronts a graph covering all 359 active BYOX entries and 82 active CSDIY courses.
Each BYOX entry has a selected builder and separate reviewer; each course has a bounded preparation,
persistent target-student kickoff, and separate examiner. These are durable planned relationships, not
claims that the projects or courses are complete.

The capability dependency is not the execution boundary by itself. At the Codex launch seam, a
deterministic runtime floor recognizes catalog and course-progression jobs through independent policy,
ID, and artifact markers, then requires `exec`/`factory-isolated` and durable `gpt-5.6-sol`/`ultra`
values. It also requires the effective provider to be `arm` at the exact configured ARM HTTPS base,
with Codex-managed OpenAI authentication enabled and WebSockets disabled; the provider display name is
not authoritative. This protects immutable legacy rows with no per-payload declaration; fresh rows
additionally carry the payload policy explicitly.

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

Every runtime BYOX code-presence gate consumes a controller-installed fresh-inode workspace rather than
the Codex-visible directory object. The old object is renamed and retired after a descriptor-relative,
hard-link-free bounded copy; a worker that retained its bind mount or file descriptor cannot resolve the
replacement. The cutover's complete checksum is required again after validation and at archive
preparation. These checks bind one detached object—they do not claim that sequential scans can prove a
still-reachable writer absent. Executable validators are excluded from this structural path.

The bootstrap Codex capability gate uses the same fresh-inode authority boundary. Its deterministic
exact-content validation, post-validation workspace checksum, and archived checksum must all match the
controller cutover record before the gate can unlock any catalog-scale dependency.

Generic CSDIY examination has a separate whole-submission boundary. The controller verifies the exact
current student artifact and serializes its learner-authored tree through pinned no-follow descriptors
into a bounded, length-framed UTF-8 projection labeled `STUDENT_SUBMISSION`. It records source artifact
identity, projected manifest/checksum, code/test inventory, and pinned inode evidence. All dependencies,
including rubrics, novel checks, and prior feedback, use the same bounded textual transport; none are
staged as files. Sensitive trees
(`sealed`, hidden tests, references, rubrics, or other-student-shaped roots) make staging fail closed;
known course inputs and disposable caches are omitted. Only `evaluation.json` and `feedback.md` are
archived, but the examiner does not write either file. It performs static review and returns one
schema-constrained final JSON object through the outer-only result channel. Only after descendant cleanup
does the controller validate duplicate-free JSON against the evaluation schema and create the two fresh
outputs. The projection checksum must equal the control-plane student projection checksum. This
contract applies to kickoff, kickoff revision, bounded unit, and unit revision examiners; revision
students receive the complete prior `student_work/` tree. A generic CSDIY verdict without this exact
binding is non-authoritative.

Static review deliberately does not execute, import, compile, or test candidate code in the examiner
context. This preserves the examiner/result-channel boundary but cannot replace executable grading.
Future candidate execution must use a separate runner with no rubric, evaluator channel, or reference
solution mounted into it and pass only bounded evidence back to the examiner/controller.

The two filesystem seams are bounded before expensive work. Student submission projection completes a
streaming no-follow preflight before allocating its destination. Dependency directories are copied by a
descriptor-relative streaming snapshot, not `copytree`, using the same CSDIY entry/file/byte/depth caps
as the textual projector. Regular files must have one link, namespace and inode fingerprints are checked
again around copy/read, and only `0o777` mode bits cross the seam. The 4,097th entry is rejected before it
is retained, opened, copied, or read.

The randomized result capability is independent of durable run IDs and is not a provenance field. Both
tool and no-tool invocations expose only a fixed outer-CLI alias; no-tool execution also uses the isolated
launch directory as its cwd. Persistent manifests and hashes encode the stable transport contract, never
the private path, nonce, or a digest derived from either. Restart recovery scans at most 10,000 entries and
128 exact channels in only the current job-attempt transport root, verifies every owner/mode/inode/link
binding, and cannot target another job or attempt. Older abandoned attempt roots are not opportunistically
deleted by a new attempt; they remain controller-private retention data until an operator has established
from the control plane that no worker owns them.

Legacy attempts, evaluations, artifacts, and knowledge evidence remain append-only history. Separate
invalidation rows remove narrative-only examiner evidence from the effective learner view, while v2
course and unit task identities prevent replacement attempts from overwriting old rows. Human learner
files are derived from this effective view and explicitly mark superseded experience. Remediation scans
read-only first and takes a SQLite writer lock only when an invalidation or safe idle-job cancellation is
actually missing.

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

Historical BYOX structural revalidation is intentionally outside attempt-scoped job validation. The
maintenance path verifies the full archived tree twice, replays the exact current code-presence policy,
classifies absent, legacy, stale, matching, or conflicting controller evidence, then appends a
content-bound observation to `byox_code_presence_audits`. Database triggers make that ledger immutable
and bind inserts to the exact artifact/job row. Multiple observations for one artifact and policy are
retained and interpreted as a conflict. The ledger is not joined into artifact labels: structural source
presence cannot establish compilation or test success.

## Trust boundaries

Source snapshots are never edited. Candidate output and grader material occupy different directories.
Copied student views and read-only, checksum-bound dependency staging remain the first structural
boundary; new Codex invocations also use the tested `factory-isolated` permission profile described
above. A host probe verifies that a job can read its workspace but cannot read a sibling sealed file or
the Codex auth file, inherit an operator sentinel, or create a network socket.

The Codex Linux permission-profile runner is beta, all host processes still share one Unix identity,
and this is not advertised as a formally verified hostile multi-tenant boundary. The configuration
requests `/proc` denial and no longer passes the final-message stream through an inherited descriptor,
but process-filesystem mediation still has nuanced exceptions and the test does not prove every process
observation impossible. Use a separately administered container/VM boundary for hostile code or secrets.
Hidden-test paths are passed only to deterministic validators in workflows that make that guarantee.

Workers, Codex commands, and validators use process sessions so routine timeout, cancellation, and
graceful shutdown can terminate their process groups. The exec backend also installs a scoped Linux
child subreaper after proving it owns no pre-existing direct child, then reaps newly adopted detached
descendants before accepting a result. A hard `SIGKILL` delivered to the supervising worker still
bypasses cleanup; descendants are not yet owned by a cgroup or parent-death signal and can survive until
an operator audits and terminates them.
