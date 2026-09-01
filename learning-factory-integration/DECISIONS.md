# Engineering decisions

## ADR-028: Bound examiner ingress before allocation and keep capabilities ephemeral

The student-to-examiner path uses one shared set of limits from source artifact through textual
projection: 4,096 entries, 2,048 regular files, 128 KiB per file, 768 KiB aggregate raw bytes, and
depth 40. Student submission projection performs a descriptor-pinned streaming preflight before it
allocates or copies a destination. Dependency staging uses a bounded descriptor-relative snapshot
instead of `copytree`; both seams reject externally hard-linked regular files, revalidate directory
names and inode fingerprints, and propagate only ordinary `0o777` mode bits. The textual projector
streams `scandir` and fails before retaining or reading the 4,097th entry.

Each final-message capability is a fresh `secrets.token_hex(32)` value independent of job, worker, and
run identifiers. Its concrete path exists only beneath an owner-only (`0700` or inherited-setgid `2700`)
controller-private per-job/attempt transport root and in runtime objects. A separate fixed-name launch
directory beneath the attempt log contains only the stable hard-link alias. The controller opens that alias read-only and no-follow, retains
the descriptor itself, and gives outer Codex only the ephemeral
`/proc/<controller-pid>/fd/<descriptor>` pathname. No-tools invocation names the held alias directory as
cwd through the same parent-procfd mechanism; tool-enabled invocation retains the workspace cwd. The
installed permission runner gives an inner tool the exact output pathname and verifies that open, read,
write, and truncate all fail, while installed outer Codex can use it for `--output-last-message` without
inheriting the descriptor. Manifests, events, run records, artifact metadata, argv, cwd, logs, and
provenance retain only the v3 nonce-free channel contract and a symbolic argv placeholder whose digest is
invariant across capabilities. Numeric PID/FD pathnames are redacted from retained text. The contract's
content-omission statement is about provenance; post-exit bounded redacted final output is still retained
normally.

A restarted backend scans only its exact attempt transport root, with a 10,000-entry and 128-channel
ceiling, and may remove an exact mode/owner/link-count-verified 64-hex crash leftover before creating the
next channel. Similar names and malformed structures are never recursive-cleanup targets. Descriptor
ownership is cleared before close so an error path cannot close a later unrelated reuse of the same FD
number. A different job or attempt root is never inspected; abandoned older attempts remain subject to
control-plane-confirmed retention rather than path-age deletion.

The path text is only an input to topology validation and a component-wise `O_DIRECTORY|O_NOFOLLOW`
walk from a trusted anchor. Each private directory is created with `mkdirat`, opened relative to its held
parent, and bound by device, inode, type, mode, owner, and link count. The fixed transport base remains
open across the CLI lifetime, but nonce-bearing job/attempt/channel descriptors are parked so they do not
become observable descriptor paths; restoration walks down from the held base and requires every captured
binding. Alias linking, capture, ordinary cleanup, spawn-error cleanup, bounded recovery, and empty-root
removal use only these held descriptors. They never mutate through a re-resolved absolute `Path`. A
missing or changed binding is evidence to preserve, not permission to unlink a same-named replacement.
The operated warehouse and log parents are setgid, so Linux legitimately creates requested mode-`0700`
children as `2700`. Both newly created and preexisting private directories therefore accept exactly
`0700` or `2700`; all group/other access, setuid, sticky, and combined unexpected special bits remain
invalid. This is deliberately non-mutating: setgid grants no access when the group bits are zero, and
retaining the full mode in the binding detects a later `0700`/`2700` change without introducing a
mkdir-to-chmod name race. Result files remain exactly `0600`.
Because POSIX does not offer inode-conditional `unlinkat` or `rmdirat`, the final check-to-removal interval
relies on the private owner-only (`0700`/`2700`) invocation directories being quiescent after the trusted
CLI and every descendant are reaped. A hostile same-UID process able to rewrite an entry inside an
already-held private directory during that interval is outside this boundary; ancestor replacement remains unable to redirect
the operation.

This decision trusts the installed outer Codex CLI as same-UID infrastructure. The enforced boundary is
non-disclosure through worker/model-visible cwd, argv, environment, provenance, and retained-log topology,
plus denial of the controller root to sandboxed tools. A compromised host CLI can recursively scan storage
or search by inode and is outside this path-secrecy boundary; use separately administered isolation for
that threat.

## ADR-027: Make CSDIY examiner results controller-owned

The previous examiner contract made its candidate tree read-only with mode bits but left the same-UID
Codex process a writable workspace containing rubric and result paths. A candidate process could attack
those paths, and an examiner-authored `evaluation.json` was not independent evidence. The controller now
builds one canonical `SandboxRuleManifest` used by both start-time provenance and the installed permission
runner. All four CSDIY examiner flows receive an entirely read-only workspace. The student projection is
copied into distinct single-link inodes and bound by device, inode, and change-time evidence in addition
to bytes and modes. Installed-profile tests exercise write, chmod, unlink, rename, directory rename,
hard-link, symlink-follow, and `renameat` attacks against protected inputs.

Rubrics, novel checks, and prior evaluations are no longer workspace files. After immutable dependency
verification the controller reads them with strict size and UTF-8 limits and appends checksum-labeled
content to the in-memory prompt. Provenance retains their source identity and checksums, not their text.
The examiner is a static reviewer: it may inspect the public read-only submission but may not execute,
import, compile, or test candidate code. Executable grading remains valuable, but it requires a separate
candidate runner that has neither rubric nor evaluator result channel; it is not silently simulated here.

The examiner returns exactly one schema-constrained JSON object through a randomized private regular file
under the controller transport root, with only a fixed alias under its isolated attempt-log launch
directory. This channel is not an inherited descriptor and is not in the worker's filesystem view. Once
Codex exits, the backend terminates its process group and, as a scoped Linux child
subreaper, kills and reaps detached descendants before validating and reading the bounded single-link
file. It fails closed if it already owns an unrelated direct child. The controller then parses the exact
two-field envelope and creates `evaluation.json` and `feedback.md` with exclusive no-follow opens. A
malformed, oversized, deeply nested, forged, missing, or multiply linked result creates no authoritative
output.

This closes the routine same-UID result-forgery and detached-child late-write paths, but not a hard kill
of the supervising worker before cleanup. A cgroup or separately administered container/VM remains the
appropriate next boundary for hostile native code and stronger process-lifetime guarantees.

## ADR-026: Re-examine CSDIY submissions through a checksum-bound whole-tree projection

The original generic CSDIY examiner received only `submission.md`, `notes.md`, and a debugging log.
Those files can describe code that the examiner never saw, so either PASS or FAIL was weak evidence.
Generic examiners now receive one protected, read-only `STUDENT_SUBMISSION/` tree projected from the
student job's exact current `VERIFIED_V2` artifact. The controller verifies the source artifact hash,
preserves every learner source/test/build-definition file, excludes staged course inputs and disposable
build caches, and fails closed if rubric, hidden, sealed, reference, or another-student-shaped material
is present. The projection records source and staged checksums, a file-manifest digest, code/test counts,
and the exact artifact/job/attempt identity. Its projected checksum must equal the checksum of the exact
read-only tree staged for the examiner, and both the tree and path-manifest digests are strict SHA-256.
Post-worker input-integrity validation must agree. The same boundary applies to initial kickoff,
kickoff revision, bounded unit, and unit revision submissions; revisions receive the full prior
`student_work/` tree instead of a narrative-only subset.

Examiner archives remain output-only (`evaluation.json` and `feedback.md`); the candidate tree is never
copied into an evaluation artifact. Learner-state publication and progression accept a generic cohort
verdict only when its evaluation evidence exactly matches the independent binding and integrity
validations. Legacy narrative-only v1 verdicts therefore remain historical but cannot unlock work.
Remediation uses deterministic v2 student and examiner job IDs plus a distinct task identity, retains
every v1 job, attempt, artifact, and evaluation unchanged, and is idempotent on reseeding. The v2 student
is a fresh attempt rather than an impossible re-grade of potentially discarded code, and keeps all
authored material under an output-only `student_work/` tree so future code is not discarded.

Legacy learner evidence is not deleted or edited. Migrations 016 and 017 add a submission-contract
revision reservation namespace and append-only attempt/evidence invalidation ledgers. Effective learner
confidence is recomputed from non-invalidated evidence, and replacement unit attempts use a separate v2
task identity. Only exact idle legacy jobs may be cancelled; active and terminal rows stay untouched.
All steady-state remediation paths discover work through read-only connections and acquire a writer lock
only after finding a candidate, followed by an authoritative recheck.
## ADR-033: Separate immutable attempt policy from runtime retry authorization

`max_attempts` remains part of an S2 job's immutable definition and binding digest. Manual retry and
graceful interruption therefore must not rewrite it. Migration 020 adds `retry_allowance`, monotonic
runtime state that the deterministic controller may increase by exactly one while reopening a failed or
blocked job, or while moving an active job to retry-wait. Eligibility, claims, failure, and lease recovery
use `max_attempts + retry_allowance`; events and operator views expose all three values. BYOX completion
authority accepts a later successful attempt only when its allowance is the minimal value implied by the
attempt number. This preserves history and restart safety without weakening immutable definitions.

## ADR-032: Content-addressed BYOX S2 publication replaces mutable legacy seeding

Every active Build-Your-Own-X catalog entry now produces a `content-v2` baseline from immutable source
and project material. Source checkout names, local paths, mirrors, ingestion times, head refs, and dirty
observations do not change identity. Builder and reviewer IDs derive independently from that baseline;
migration 019 stores the material snapshot, binds each complete job definition and dependency set to it,
and prevents in-place definition or binding changes.

Cutover recognizes only complete controller-released legacy definitions. It reconstructs historical
source observations from the stored payload, verifies that their material still derives the current
content baseline, and then compares the entire builder/reviewer definition. Exact queued work is retired
atomically before S2 publication. Exact active work receives a cancellation request and publication is
deferred until reconciliation. Terminal history and attempt evidence are preserved. Relocating a source
therefore does not strand authentic legacy work, while prompt, model, dependency, source material, or
oversized/malformed-locator changes fail closed.

Remediation replay similarly admits current S2 evidence or narrowly enumerated released histories; it
does not infer legacy authority from shape alone. Four pre-policy generic histories and the KV-v1 history
remain quarantined because they lack sufficient externally validated policy/evidence. KV-v2, HTTP,
allocator, and bytecode histories have exact job-specific replay profiles. Programmatic BYOX publication
requires a canonical absolute `warehouse` path so cutover reachability and artifact boundaries cannot be
derived from the process working directory.

## ADR-031: Replace BYOX reviewer commands with a versioned deterministic contract

> Historical pre-S2 policy. ADR-032 supersedes its in-place upgrade and versioned-successor seeding
> mechanics; the deterministic review evidence contract itself remains in force inside S2 definitions.

The original BYOX reviewer payload used a host `command` validator to check that `evidence` and
`checks_run` were populated. Production deliberately fences that execution path, so otherwise safe
reviewers could remain READY without an attempt. Reviewer verdict contract version 2 moves the same
check into `review_verdict`: `evidence` and `checks_run` must be nonempty arrays, and every entry in
those arrays and `limitations` must be a nonempty, exactly trimmed string. Its durable evidence records
the contract version, entry counts, and evaluation-file SHA-256. The exact BYOX bundle contains only
required-path, schema, versioned-verdict, and closed-acceptance validators; executable or additional
validator specs are not recognized as this contract.

Never-attempted DISCOVERED, READY, RETRY_WAIT, or BLOCKED seed rows may receive this definition in
place. Attempted definitions and terminal rows are not rewritten: policy version 3 is the first
deterministic successor for deployed v1/v2 reviewers, and later conflicting attempted successors advance
monotonically. Active attempts finish before a successor is selected. Re-seeding preflights historical
rows with a read before taking an NFS-backed SQLite writer lock, so an already-converged graph is a true
read-only no-op. The same attempt-zero rule persists the existing BYOX code-presence gate into safe
generic-builder payloads without changing attempted builder history.

Remediation consumes only a checksum-bound review carrying the exact payload contract plus one passing
current-attempt required-files result, schema result, versioned verdict result, and non-executable
closed-acceptance result. The required-files row is canonical and binds exactly `EVALUATION.json`,
`REVIEW.md`, and `VALIDATION.md`; it cannot carry claims or command fields.
The former command-validation row is neither required nor trusted. Closed acceptance remains advisory:
it emits no `REVIEWED` claim and cannot turn reviewer PASS into workflow acceptance.

Contract-version matching is type-strict: only JSON integer `2` is valid, never `2.0`, `true`, or an
ambiguous duplicate-key decode. Remediation reopens every absolute archive component through retained
directory descriptors with `O_NOFOLLOW`, then performs one bounded tree pass. The pass reads every
unaliased regular file once for the complete `tree-sha256-v2` digest and captures all three required
files plus their hashes from those same reads. Directory discovery retains at most the remaining global
entry allowance; final name revalidation reads at most the expected count plus one mismatch sentinel.
A final descriptor-relative manifest and absolute-root revalidation detects content, inode, name,
directory, and root sandwiches. The builder archive is independently snapshotted and must match its
current artifact identity, path, checksum algorithm, checksum, attempt, and the exact ordered
validation-status/label evidence admitted for that profile. Gate, builder, and review paths must resolve
through that same pinned chain below `Database.path.parent / "artifacts"`; lexical prefixes, symlink
ancestors, and matching trees elsewhere on the host are not accepted.

The pinned chain intentionally compares shared absolute ancestors by device/inode identity instead of
requiring their mutable metadata to remain unchanged. If a shared ancestor is briefly renamed and the
same inode is restored, open descriptors continue to select the original bytes and final identity checks
still pass; this avoids rejecting safe concurrent namespace churn. A replacement cannot redirect a read,
and a replacement left in place or restored under a different inode fails closed. The artifact root and
all artifact entries retain the stronger metadata checks.

The base reviewer payload, its exact gate/builder dependency set, every candidate
subpath/destination/type expectation, the sole protected root, and the archived staging bindings must all
equal their canonical definitions. A generic base builder must equal the complete job specification
rebuilt from the active catalog: job ID, type, worker role, priority inputs and result, retry bound, model,
reasoning effort, exact gate dependency, and the full payload. The only payload alternatives are the two
whole encodings actually released by the controller: the original job-factory payload with its
model-only execution policy, and that exact payload transformed by the current backend-policy helper.
Partial policy additions and all other extra, missing, type-changed, or value-changed fields fail closed.
Reviewer expectations use the freshly rebuilt matching payload rather than the stored object. Legacy
specialized builders remain accepted only when the complete deterministic specification reconstructed
from the active catalog matches; a merely recognized job type or coherently rewritten profile is
insufficient.

The active BYOX query, strict row normalization, requested-project filtering, scan bound, canonical job
reconstruction, and remediation publication execute on one connection under one `BEGIN IMMEDIATE`
transaction. A concurrent ingestion writer therefore commits either before the snapshot query or after
the remediation transaction, never between snapshot selection and publication. Every accepted reviewer
must also be a `codex_task` examiner using `gpt-5.6-sol` with `ultra` reasoning. Generic base builders,
completed repair builders, and reviewers must have a controller-reachable successful execution envelope:
the canonical retry ceiling, an exact integer current attempt from 1 through that ceiling, nonnegative
finite
`created <= started <= finished` timestamps, cleared owner/lease/retry/error/failure fields, and no
cancellation. The current artifact and review validations must bind the same attempt. A nonterminal repair
builder retains `WAITING_FOR_REPAIR_BUILDER`; once it claims `SUCCEEDED`, this envelope is required before
publishing its reviewer or any later repair generation and is rechecked during repair-review validation.
`job_runs` remains observability rather than completion authority because its final exit metadata is
written after the atomic job/artifact success transaction and older durable rows may legitimately lack it.

The original KV v1/v2, HTTP, allocator, and bytecode slice seeders and remediation use one shared set of
pure constructors over normalized active-catalog snapshots. These constructors reproduce every released
field, including selectors, payloads, priorities, score components, retry ceilings, null model/reasoning
values, and dependency sets. Remediation derives the set from the complete active snapshot inside its
existing publication transaction before applying request/scan bounds. A specialized artifact is therefore
reviewable only when its entire persisted job and terminal execution envelope match a constructor; a
source revision or partial historical-shape hybrid fails closed. Released builder payloads omitted
`artifact_type`, so that raw representation is matched exactly and the verified type is added only to a
fresh reviewer-facing copy.

Verdict identity, counts, recommendation, workflow state, and SHA-256 come from the captured evaluation
bytes. Runtime schema and verdict validators apply the same 1 MiB pre-allocation bound. Stored payloads
on seeding, dispatch, and remediation paths use one bounded decoder that accepts only exact built-in text
or bytes and applies explicit lexical nesting, token, node, string, number, and sign-aware integer limits
before recursive decode. These limits are independent of mutable interpreter integer settings. Duplicate
keys at every level, unpaired surrogates in keys or values, non-finite numbers, and pathological nesting
are rejected instead of normalized. Valid Unicode remains accepted. Artifact identity and attempt
bindings are type-strict, so `true` and `1.0` cannot impersonate attempt `1`. The persisted status string
must exactly equal its canonical ordered label rows; `BLOCKED` and `REVIEWED` are not positive closed-pair
evidence. Gate/reviewer artifacts require `GENERATED`, generic/repair builders require
`GENERATED+PARTIAL`, and historical specialized builders may retain only backed, admitted nonterminal
labels.
## ADR-024: Fence host-command validators independently of job dispatch

An untrusted validation command must not run through the legacy host `Popen` path while the replacement
sandbox is under review. The scheduler therefore defaults `allow_host_command_validators` to false and
atomically skips READY jobs containing either a `command` validator or command-mode
`review_acceptance`. A malformed validator envelope is also held whenever this fence is active. Held
jobs remain durable and READY: they receive no owner, lease, attempt, failure, or synthetic completion,
and lower-priority structural work remains claimable.

The bootstrap backend-capability gate must itself remain claimable on a fresh database. Its exact output
check is therefore a deterministic `input_integrity` SHA-256 assertion, not a privileged exception to the
command fence. The handler also retires the Codex-visible tree and installs a fresh-inode snapshot before
validation; post-validation and archive checksums are bound to that cutover record. All catalog-scale
dependencies can unlock without enabling legacy host execution.

Payload inspection cannot see validators synthesized by deterministic handlers. The worker therefore
repeats the fence over the actual `HandlerResult.validators` immediately before `Validator.run` for
every job type. A generated executable or malformed envelope becomes `BLOCKED` without launching a
validator process. BYOX structural candidates additionally forbid mixing executable validators with
their detached-snapshot contract even if the operator enables the legacy host escape hatch.

This is a dispatch safety control, not a validator implementation and not evidence that a held job
passed. Status reports the blocked validator category and exact current READY count. The switch may be
enabled only in a deliberately isolated test configuration until an independently reviewed sandbox and
immutable-grader integration replace the host path. Catalog-scale production keeps it disabled.

## ADR-025: Make CSDIY examination a no-tool textual protocol

CSDIY examiners do not need a compiler, shell, candidate mount, or writable workspace to perform their
current static-review role. The controller therefore converts every verified dependency to a strict,
bounded UTF-8 tree projection through pinned descriptor-relative no-follow traversal. Their workspace is
empty and root-denied and all known command/execution/artifact surfaces are explicitly disabled under
strict Codex configuration. A separate future runner must execute candidate code and return bounded
evidence; it must never share the examiner's rubric or output channel.

The outer Codex CLI alone publishes its final response. A randomized mode-private inode is linked to a
fixed alias in the isolated launch directory beneath the job log, while its path remains under the
separate controller-private attempt root; only the alias appears in CLI state. Device, inode, mode,
owner, and exact link count are checked before and after execution, the alias is unlinked via a pinned
directory descriptor, and only the resulting single-link private inode is read. This keeps the random
token out of process metadata without granting the inner sandbox result-directory access. Schema-invalid,
duplicate-key, partial, oversized, or deeply nested JSON creates no outputs. Global idempotent seeding
reconciliation cancels every ownerless claimable legacy examiner lacking the submission binding and
durably requests cancellation for active ones while preserving prior attempt rows.

## ADR-023: Cut BYOX validation over to an authoritative fresh snapshot

BYOX repair workers may leave useful selected output beside undeclared or otherwise unsafe roots. Before
validation, the controller captures selected output and protected staged inputs exactly once through
descriptor-relative, no-follow reads into new factory-private inodes. It rejects special files,
cross-set hard links, rebindings, malformed staged manifests, and byte or entry budget violations. Roots
outside the selected contract are never promoted: bounded metadata and content hashes are retained in a
quarantine manifest for evidence only.

The freshly captured tree atomically replaces the allocated attempt path; the original worker tree is
renamed to a retired location and then discarded. A Codex process that retained its bind mount, path, or
file descriptor therefore remains attached to the retired directory object and cannot mutate the fresh
snapshot. Validators and archiving see only the replacement. Before publication, the worker recomputes
the complete snapshot and requires its checksum, selected-projection checksum, staged-input bindings,
cutover record, quarantine-manifest link, validation-workspace checksum, and eventual archive checksum to
agree. Cutover records use a canonical four-field staged-binding projection while retaining richer
metadata separately, preventing recomputation or record-splicing from changing authoritative input
identity.

The same boundary now covers every ordinary `byox-challenge-pack` carrying the structural code gate.
For those packs the complete candidate is copied to fresh inodes and its full-tree checksum is recorded
before any authoritative validator. The worker requires that exact checksum after validation, at the
archive-candidate boundary, and after archive preparation. This is not a claim that repeated scans make
a live tree atomic: authority starts at the writer-inaccessible replacement object. A finite sequence of
rechecks remains only defense in depth.

Historical attempts with neither cutover record remain readable under their prior contract; a partial,
malformed, contradictory, or one-sided record fails closed. These cutovers solve the worker-writer and
repair-projection boundaries only. They do not waive independent code-presence, build, test, review, or
transfer validation.

## ADR-022: Enforce the mass Codex backend floor at the launch seam

The original catalog-scale CSDIY/BYOX jobs predate per-payload backend declarations and remain
immutable evidence. They are not rewritten. Before any applicable Codex launch, the handler now
recognizes the graph independently by seed-policy kind, stable job-ID shape, or artifact type and
requires the effective backend to be `exec`, its permission profile to be `factory-isolated`, and the
durable job columns to specify `gpt-5.6-sol` with `ultra` reasoning. The same seam requires provider
`arm`, the exact `https://openai-api-proxy.geo.arm.com/api/providers/openai/v1` base URL,
Codex-managed OpenAI authentication enabled, and WebSockets disabled. `provider_name` remains a
display-only value. Conflicting explicit declarations or effective route settings fail closed as
non-retryable backend-configuration errors. This includes bounded CSDIY progression and revision
graphs plus BYOX remediation builders/reviewers, not only initial catalog coverage.

Fresh mass-seeded and course-progression jobs carry both `required_backend` and the full execution
policy. Compatibility is limited to exact historical shapes: complete omission, the original BYOX
builder's two quality fields, and the already-fenced kickoff revision's `required_backend`. The two
partial exceptions require mutually consistent policy, role, artifact type, worker type, and stable
job-ID family; BYOX additionally recomputes its job ID from `project_id`, while kickoff binds the
revision ID and role-specific suffix. Arbitrary partial or conflicting declarations are rejected, and
deterministic identity comparison normalizes only a complete policy versus complete omission.
Recognition applies only to `codex_task`, leaving deterministic fake/local jobs unchanged.

## ADR-021: Revalidate archived BYOX code presence in a separate append-only ledger

Previously archived BYOX packs may predate the authoritative code-presence validator. A bounded
`revalidate-byox-code` maintenance command now checks them without reopening their completed job
attempts or manufacturing historical validation rows. It verifies a canonical in-warehouse path,
rejects symlinks and special files, and makes a bounded no-follow copy in a random factory-owned private
directory. The copied tree and its immutable manifest must equal the stored framed checksum; the exact
current gate runs
only as a pure function over the copy's immutable metadata/content-hash manifest, whose independently
derived V2 tree checksum must also match. Source rechecks detect common drift but do not purport to make
a concurrently mutable live tree atomic; the stored-checksum-identical private copy is the evaluated
authority. The retained observation
binds artifact, job, physical attempt, stored/source/copy/manifest checksums, job-payload hash, policy
digest, canonical policy-spec hash, and manifest audit protocol without retaining its temporary path.

The dedicated table is append-only by trigger and deterministic observations are idempotent. If the
same stored artifact/policy later produces different evidence, both observations survive and the
effective result is `CONFLICT`; nothing is overwritten. Existing controller gate rows are classified as
absent, legacy-unbound, stale-policy, exact-final-policy, or conflicting. This ledger never changes an
artifact label, validation row, job, or archive tree, and its `PASS` scope is fixed to code-presence
structure only. In particular, builder-authored build reports and source-file presence cannot mint
`BUILDS` or `TESTED`.

All hash and copy reads—including reads from a tree later rejected for a symlink, hard link, special
file, depth, or other structural fault—charge one aggregate byte budget. The shared directory-depth
bound is enforced before recursive work in capture, copy, and checksum paths. Wall expiry is checked
inside the append transaction immediately before returning an existing row or inserting/committing a
new row; an exhausted invocation remains resumable and emits no audit observation.

## ADR-020: Reject controller credentials before job persistence

`JobRepository.create` serializes each payload once, then scans it for exact values obtained only from
credential-classified controller environment names. Qualifying values are normalized and encoded as
JSON string content so escaping cannot bypass the check. Matches and provider failures abort before the
SQLite transaction with generic errors; values, names, and hashes are never emitted. Short values,
known placeholders, clean endpoint URLs, and file/path references are excluded to avoid treating normal
educational prose as a secret. This is defense in depth for repository-created jobs, not a replacement
for process-environment isolation or a guard on deliberate direct SQL writes.

Backend configuration separately rejects endpoint URLs containing user information, query strings,
fragments, control characters, non-HTTP schemes, or missing hosts before such routing metadata can be
stored in a run record.

## ADR-019: Fingerprint executable state at the start of every new job run

Every new `job_runs` row records `learnfactory-run-provenance-v3`: a combined SHA-256 over separate
execution-code, allowlisted configuration, authoritative job-policy, and safe execution-envelope digests. The
code component hashes tracked plus non-ignored untracked files only in execution-relevant repository
paths, records the Git commit and dirty path sets, and reports bounds or races instead of pretending a
partial observation is complete. Raw config, environment values, prompts, payloads, file contents, and
credentials are never copied. Credential-free payloads and effective prompts receive exact byte hashes;
detected credential-bearing values are redacted before hashing, marked `safe-redacted-envelope`, and never
represented by a hash of the raw secret.

The exec backend's invocation manifest and launcher share argv and leaf-worker prompt-envelope builders.
It therefore binds the resolved Codex command, secret-free config flags, permission profile, toolchain
roots, endpoint routing, timeout, output-schema hash, effective model/reasoning, leaf-policy hash, and
effective stdin hash. SQLite is authoritative; a mode-`0600` `RUN_PROVENANCE.json` beside logs is the
human-readable view, and successful artifact metadata links the same digest. Pre-migration history is
not backfilled because its exact start-time state cannot be reconstructed honestly.

## ADR-029: Keep SQLite on rollback journal while removing NFS write amplification

The authoritative database remains SQLite in `DELETE` journal mode: this host uses NFSv3, so WAL's
shared-memory assumptions are not accepted. Ordinary connections do not assign journal mode; migration
verifies it and changes only an incompatible database. Migrations otherwise have a no-write
compatibility fast path and acquire one lock only when work is missing, operator status opens a verified
query-only database, and idle scheduler probes do not acquire write transactions. Compact indexes, one
indexed row-value cursor over independently released bounded pages, deterministic legacy/v2 job-ID
range queries, and fixed maintenance/refill cadences reduce table and payload scans without weakening
atomic claims or starvation behavior. Payload parsing never retains a SHARED lock. A trigger-maintained
scheduling-projection generation fences changes between selection and the writer transaction, which
rechecks that generation and every authority predicate for the selected ID. Missing cursor schema fails
closed during rolling migration. Kickoff revisions are scanned and course-grouped once per refill.
Dependency edges participate in the same generation. Their identity freezes when a child leaves
`DISCOVERED`: a delete guard rejects direct edge removal and prerequisite-side cascades, while SQLite's
child-side cascade still removes edges during whole-child retention cleanup. Claim and success boundaries
query the current prerequisite states with missing parents treated as unsatisfied; success performs an
early publication check, exact edge/prerequisite-state and dependency-schema comparison around hooks, a
final conditional update, and a schema-level invariant. Dependency publication failures roll back hook
DDL and data rather than exposing an artifact from an invalid graph.

`pause` is linearized against claims in the database. Busy-timeout configuration must leave headroom
between a heartbeat and lease expiry. Worker start renews the durable lease, and contention retries
dynamically cap each possible SQLite lock wait inside the remaining budget. An independent monotonic
watchdog cancels before the last confirmed expiry even if a heartbeat later commits successfully.
Heartbeat failures are observable rather than silently swallowed. Final publication first quiesces and
joins heartbeat and watchdog, then checks local/durable/supervisor cancellation while holding the
publication gate through the success commit. An in-flight heartbeat that returns lease loss after stop was
requested still cancels. The final check is the local-stop/SIGTERM linearization point; a later SIGTERM
does not revoke a publication already in progress, while durable operator cancellation remains checked in
the SQLite transaction. Concurrent WAL normalization closes and reopens contending connections so one
process can converge the journal mode. Changing to WAL, moving the database off NFS, or introducing a
service database remains a separate measured migration decision.

## ADR-030: Scope in-transaction publication callbacks

Artifact publication occasionally needs an atomic source-catalog or learner-evidence side effect, but
the callback is not part of the scheduler control plane. The orchestrator therefore assigns one of two
non-overlapping scopes and passes a typed connection/cursor facade rather than a raw SQLite connection.
Source ingestion cannot mutate learner records; learner activation cannot mutate the catalog; neither can
mutate jobs, dependencies, artifacts, workers, validation records, migrations, attached databases, or
schema. A temporary authorizer independently enforces table and operation permissions and restores the
previous authorizer afterward. Python's SQLite statement cache is disabled because SQLite 3.26 otherwise
reuses pre-authorized statements across the temporary policy boundary.

This is defensive least privilege for trusted, deterministic in-process factory callbacks. It prevents
accidental API/SQL authority escape; it is not a sandbox against arbitrary Python reflection, importing
`sqlite3`, or reopening the database path. Untrusted/model-generated code remains process- and
workspace-isolated and never runs as a publication callback.

## ADR-018: Raise operated concurrency to 12 and run continuously until idle

The operated scheduler ceiling is 12, with principal role limits of five reference builders, two course
managers, two students, and three examiners. SQLite claims remain the shared capacity authority, so
multiple controllers cannot exceed these limits by racing. A continuous `run --until-idle` controller
is active and refills slots as dependencies become eligible. This is bounded pressure, not an assertion
of unlimited endpoint capacity; throttling and failure evidence still govern retries. `--max-jobs` is an
invocation-level dispatch budget and was used for the earlier three-job probe, not as the steady-state
concurrency setting.

## ADR-017: Continue CSDIY courses in one-record, examiner-gated batches

`seed-course-next` may add at most one normalized resource record per eligible course per refill. It
requires current checksum-verified preparation and predecessor-examiner artifacts plus a
control-plane-published PASS. Each batch receives an independent materializer, persistent target
student, and examiner workspace. Batch identities bind the source commit, input artifacts, learner
snapshot, and record selection; partial graph creation is repaired idempotently. The command is a graph
refiller, never a completion detector: record exhaustion, an examiner PASS, and even every seeded batch
succeeding still carry `course_completion: NOT_CLAIMED` and no transfer-verification claim.

A kickoff `REVISE` or `FAIL` now enters the same configured finite revision budget instead of stalling
the course forever. Each ordinal is a fresh student/examiner pair whose immutable identity binds the
exact prior student artifact and the examiner's learner-facing feedback; the student never receives the
rubric, hidden checks, references, or another learner's work. Jobs themselves are the concurrent-safe
reservation, and the existing revision-block ledger records exhausted limits under a namespaced kickoff
scope. Reporting follows only a contiguous checksum-bound ordinal chain; forks, gaps, or conflicting
evidence cannot turn into a PASS claim. The refiller uses the same fail-closed rule: it never selects an
evaluation by newest timestamp, and contradictory same-attempt result, evaluator, rubric, or artifact-
attempt bindings cannot schedule a revision or unlock the next unit.

## ADR-016: Archive BYOX review outcomes separately from accepting candidates

A review validator accepts exactly `PASS`, `REVISE`, or `FAIL` as valid recorded outcomes. Negative
outcomes still produce useful review artifacts and may let the review job itself succeed. Reviewer
`PASS` is advisory and never emits the `REVIEWED` claim. Acceptance is delegated to a distinct
`review_acceptance` validator whose safe default is closed; command mode must capture independent command
evidence and bind the exact current builder/reviewer artifacts before it can mint `REVIEWED`. Reporting
requires that acceptance evidence and fails closed on conflicting, missing, ambiguous, or review-only
evidence. Attempted v1 review jobs remain immutable historical evidence; remediation supersedes them by
provenance instead of rewriting history.

## ADR-015: Use a fail-closed Codex permission profile for new model jobs

New `codex exec` and resume invocations use a named `factory-isolated` profile instead of `--sandbox`.
The backend ignores user config/rules, requires strict config, denies `:root`, grants `:minimal` plus the
resolved Codex executable and explicitly allowlisted toolchain roots read-only, writes only the job
workspace, disables worker-tool network, inherits no shell environment, and denies `CODEX_HOME`.
Hosted/web, MCP, browser/computer-use, plugin, skill-discovery, hook, and native subagent surfaces are
disabled so operator extensions cannot silently widen a worker's authority. Configuration is rejected
before spawn when an allowlisted toolchain root is relative, overly broad, protected, or overlaps auth
storage.

This materially improves the same-UID boundary and has a live host probe, but Codex's Linux permission
profile is beta and is not claimed as formal hostile multi-tenant isolation. ADR-027 replaces the
inherited final-message descriptor and specializes the CSDIY examiner rules; it does not prove every
process-filesystem observation impossible. Containers or VMs remain appropriate for hostile code and
secrets.

## ADR-014: Backend-gated all-catalog job graph

> Superseded for BYOX selection by ADR-032. The capability gate and CSDIY coverage policy remain active.

One externally validated capability job gates mass Codex dispatch. After it succeeds, every active CSDIY
course has a bounded manager/student/examiner kickoff graph and every active BYOX entry has one selected
builder plus an independent reviewer. Pre-S2 specialized reuse is retained only as historical evidence;
current BYOX coverage uses baseline-bound S2 pairs. Graph coverage is reported separately from job success, artifact
validation labels, transfer evidence, and course completion.

## ADR-013: ARM custom provider with Codex-managed authentication

The enabled exec backend uses provider `arm`, base
`https://openai-api-proxy.geo.arm.com/api/providers/openai/v1`, the Responses wire API, and WebSockets
disabled. The provider reuses authentication through Codex's supported auth mechanism. Factory TOML,
SQLite, prompts, generated artifacts, and documentation must contain routing metadata but never the
credential itself. A versioned, bounded gate job is the end-to-end operational check; stale failures from
the former default endpoint remain history until explicitly retried.

## ADR-011: Independent prepublication review for deep generators

A generator passing its own validators is necessary but not sufficient for a deep challenge pack.
Before first publication, a separate context probes semantics, isolation, failure boundaries, claim
honesty, and benchmark design. Confirmed defects become executable regressions; the job stays paused
or undispatched until the independent reviewer reports no remaining blocker under its explicit
validation labels. This gate found material issues in every initial networking/scale-out candidate.

## ADR-012: Generated artifacts identify their factory revision

New artifact metadata records the Learning Factory Git commit and whether tracked files were clean
when the validated tree was prepared. Untracked warehouse output is excluded from the cleanliness
check so bounded concurrent publications do not make one another appear to use modified generator
code. Source commits and job/run IDs remain separate provenance dimensions.

## ADR-009: Standalone Codex worker quality profile

Standalone Codex CLI jobs default to model `gpt-5.6-sol` with reasoning effort
`ultra`, per the operator's explicit instruction. The values remain configurable
and are persisted on each job run; deterministic ingestion and validators do not
invoke a model. Provider routing and authentication are governed separately by ADR-013.

## ADR-010: Immutable source history with one active snapshot

Every observed source commit and its normalized rows remain durable provenance.
Exactly one snapshot per canonical repository path is active; publication selects
the most recently prepared snapshot under `BEGIN IMMEDIATE` and marks older rows
as superseded. Catalog consumers join through the active source instead of deleting
history. Scheduled ingestion prepares without DB writes, then activates inside the
same lease-fenced transaction that archives the validated artifact and succeeds the
job.

## ADR-001: Python 3.11 and standard library

The host has Python 3.11 and SQLite but not pytest. The initial system therefore uses `asyncio`,
`sqlite3`, `unittest`, TOML, and subprocesses without third-party runtime dependencies.

## ADR-002: SQLite with rollback journal

SQLite is authoritative. The workspace is NFS-mounted, so rollback-journal mode is safer than assuming
WAL shared-memory semantics. `busy_timeout`, foreign keys, explicit transactions, and `BEGIN IMMEDIATE`
provide bounded multi-process coordination.

## ADR-003: Stable Exec backend first

Installed Codex 0.146.0 exposes stable noninteractive JSONL through `codex exec --json`; app-server is
explicitly experimental. Both fit the backend interface, but exec is the enabled implementation.

## ADR-004: Semantic archive plus hashes, not a CAS

Humans browse semantic paths while SQLite stores SHA-256 tree hashes. A full content-addressed store is
deferred until duplicate volume justifies it.

## ADR-005: Honest isolation labels

Student views structurally exclude sealed material and escaping symlinks. Local same-user execution is
not advertised as a formally verified hostile security boundary; artifacts record `ISOLATED_VIEW`
rather than claiming container isolation. ADR-015 supersedes the original advisory Codex sandbox with a
tested, fail-closed permission profile while retaining that honest limitation.

## ADR-034: Evidence-derived BYOX remediation authority

BYOX remediation uses frozen controller specifications plus independently captured evidence, not mutable
historical rows as templates. Current and deployed-legacy capability gates are whole-spec alternatives.
Builder artifacts have one canonical semantic destination, descriptor-safe bytes, code-bearing structure,
and validation/label metadata derived exactly from all current-attempt PASS records. Review successor
history admits only enumerated released payload forms and controller-reachable, time-ordered terminal states.

Modern repair cutovers are authenticated against their canonical four declared inputs and the actual
source/artifact manifests. Compatibility for pre-cutover output is an explicit seven-item attempt-1
identity registry. This narrow allowlist was chosen over a structural “missing cutover means historical”
rule because the latter could mint new legacy authority by coherently rewriting mutable database fields.
