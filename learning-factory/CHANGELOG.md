# Changelog

## Unreleased

- Expose the exact Arm GNU 15.2.Rel1, QEMU 9.1.1, and QEMU GLib 2.82.1
  installation leaves read-only to tool-enabled isolated workers. Keep the broad
  `/arm` and `/arm/tools` trees denied, and retain absolute-path discovery and
  provenance for every configured root.
- Reconcile strict BYOX replay with the handler's fresh-inode staging records. Replay now
  accepts only the exact legacy semantic record or that record plus the complete,
  structurally valid runtime inode-evidence set; it still reconstructs and exact-compares
  every durable artifact binding. Independent-review integrity evidence is checked against
  the canonical protected root rather than synthetic leaf records, and the same projection
  rule covers repair cutovers. Production-shaped regressions prevent either reader/writer
  schema from drifting again.
- Bound the publication-time factory revision probe to the same execution-relevant paths as
  run provenance. This avoids full-corpus Git scans on NFS, and a later diff failure now
  retains the already-resolved commit while reporting status as unavailable instead of
  discarding that evidence.
- Add a one-shot exact-job scheduler mode, `run --job JOB_ID`. It bypasses
  global READY priority without falling back to another job, suppresses all
  catalog refills, retains pause/dependency/attempt/capacity/validator fences,
  drains at most the one claimed worker, and records the exact target in
  scheduler lifecycle events. This makes deliberate historical retries
  operable without dispatching unrelated queued work.
- Reap subreaper-adopted exited Codex descendants throughout long backend
  calls while preserving exclusive `Popen` ownership of the primary wait
  status. Cleanup now makes a final direct kill/reap attempt even when process
  group signaling fails and fails closed if the primary cannot be proved
  terminal before descendant reconciliation and subreaper restoration.
- Disable Git's legacy diff index auto-refresh and its modern optional locks for
  bounded read-only run-provenance queries, so a query timeout on a large NFS
  worktree cannot strand the root repository's `index.lock` and block later
  checkpoints.
- Preserve the initial catalog refill for unpaused bounded scheduler runs, including the intentional
  `--max-jobs 0` refill-only operation, but suppress that controller's periodic refills after it reaches
  a finite dispatch ceiling. This removes avoidable rollback-journal writer contention while the bounded
  run drains its workers without claiming database-global coordination with other controllers or seeders.
- Preserve protected-input integrity across authoritative BYOX workspace cutover. Verify the original
  content and inode evidence before copying, require the installed snapshot to retain the exact semantic
  bindings, and rebind only its intentionally fresh inode evidence for validation. Same-byte inode swaps
  remain detectable both before and after cutover without falsely rejecting the controller's own copy.
- Preserve immutable source provenance after consolidating the workspace under one top-level Git
  repository. `SOURCE_PINS.json` binds each vendored source path to its audited upstream commit, tree,
  remote, and branch; ingestion verifies the committed outer-repository subtree has the exact pinned tree
  before reading blobs from Git, scopes dirty-state reporting to that source, and fails closed on drift.
- Start a de-synchronized claim heartbeat before any worker workspace or provenance I/O, carry one
  non-decreasing monotonic deadline across the claim/start boundary, and fence cancellation or lease loss
  before handler execution. Atomically commit worker/run registration with `CLAIMED` to `RUNNING` so
  recovery cannot expose a running worker for a claimed job or leave an open run after a lost start race.
  Spawn the worker before controller-side NFS log-directory creation, and add real-lock, short-lease,
  cancellation/recovery, out-of-order-renewal, and state-pair regressions.
- Increase the operated lease from 30 to 120 seconds after the first 12-slot launch wave showed that
  concurrent provenance capture and NFS SQLite writer contention could consume the entire shorter claim
  lease before workers established steady heartbeats. The deterministic lease-loss fence correctly
  prevented publication and recovered every job. Increase the database busy timeout from 20 to 60 seconds
  after a valid course preparation then hit the shorter window during controller-owned finalization; the
  heartbeat path still caps its own waits before durable expiry. Retain these wider windows while the new
  startup protection is canaried at production scale; reducing them is a separate measured change.

- Make CSDIY examiner results controller-owned and eliminate their local attack surface: project every
  verified candidate/rubric/prior-evaluation dependency through pinned no-follow descriptors into bounded,
  checksum- and length-framed UTF-8 prompt text; launch with an empty root-denied workspace, no inner
  filesystem rules/toolchain, and command/code-mode/artifact/deferred/hosted capabilities disabled.
  Keep the randomized result token out of argv, environment, cwd, descriptors, prompts, logs, and inner
  rules by separating its controller-private per-job/attempt root from a nonce-free launch directory that
  contains only the pinned fixed-name outer-CLI hard-link alias; reject namespace, alias, parent-swap,
  rebinding, and link-count races. Component-walk every ancestor with no-follow directory descriptors,
  perform all transport/alias creation and removal relative to retained bound parents, and park randomized
  descendant descriptors at the fixed transport anchor while the CLI runs. Restore only matching captured
  inode/type/mode/owner/link bindings; on uncertainty preserve evidence rather than re-resolving a path or
  touching a same-named replacement. Hold a read-only descriptor for the fixed alias and give the trusted
  outer CLI only its ephemeral parent-procfd pathname; inherit no result descriptor, deny the exact path to
  sandboxed tools, use a symbolic durable argv placeholder, and redact numeric PID/FD paths from retained
  text. Derive the 256-bit capability independently of durable IDs, persist and
  hash only its v3 nonce-free contract, and reclaim exact verified crash leftovers with bounded recovery
  scoped to one attempt. Clear descriptor ownership before close, never scan another attempt during
  recovery, and leave old-attempt removal to control-plane-confirmed retention. Accept only owner-only
  private directory modes `0700` and inherited-setgid `2700`, bind the full mode without chmod, and reject
  group/other access, other special bits, wrong owners, symlinks, and later mode transitions so the
  operated setgid warehouse/log filesystem remains launchable without weakening the capability boundary.
  Stream and preflight student/dependency trees under shared entry/file/byte/depth limits, fail before
  retaining or reading entry 4,097, reject external hard links and rename races, and propagate only rwx
  mode bits through controller-owned copies.
  Reconcile detached descendants, require duplicate-free schema-valid JSON, publish neither file on any
  rejected envelope, globally cancel every ownerless claimable legacy examiner without a submission
  binding, and request cancellation for active ones while preserving attempt and terminal history.
- Replace raw SQLite publication-hook access with orchestrator-selected source/learner scopes, a typed
  connection/cursor/iterator facade, and a temporary restoring authorizer. Revoke retained facades on
  callback exit and serialize revocation/restoration with every complete SQLite operation. Atomically reject
  controller connections with a tracked pre-existing authorizer because arbitrary reentrant callbacks
  cannot be safely composed. Guard authorizer ownership with an opaque connection capability, sticky-deny ordinary
  replacement, and unconditionally reinstall policy before SQL so direct base-descriptor replacement
  between operations cannot bypass Python tracking. Deny transaction control,
  savepoints, scripts, pragmas, attachment, DDL, extensions, control-plane mutation, cursor escape, and
  cross-domain writes; disable SQLite statement caching to close pre-authorized-query reuse. Add atomic
  adversarial rollback, sticky-denial, and authorizer-restoration coverage; classify scope violations as
  permanent publication failures rather than dependency blocks. Reorder late-heartbeat processing so expiry
  wins over publication stop, and coherently reclassify concurrent SIGTERM as interrupt/exit 143.
- Harden SQLite scheduling on NFS: make pause and its event atomic and linearize every claim against the
  durable pause flag; resample pause after refills and between launches; cadence maintenance/refills;
  avoid no-op write transactions; select candidates through independently released bounded read pages
  and an SQLite-3.26-linear persisted row-value cursor; fence selection races with a trigger-maintained
  projection generation; exclude saturated worker types; and scan/group legacy/v2 kickoff revisions once
  per course refill. Make status query-only, collapse missing migrations under one write lock, normalize
  incompatible WAL databases safely across processes, renew leases at worker start, dynamically cap both
  possible heartbeat lock waits, and add an independent durable-expiry watchdog. Add real lock/race tests,
  equal-priority production-helper VM-step measurements, and preserve expired leases for authoritative
  LOST-worker recovery. Fence final publication by quiescing and joining heartbeat/watchdog, treat local
  lease loss as a retryable interruption at every major worker boundary, and define/test the final
  SIGTERM linearization point.
- Make dependency graphs authoritative at dispatch and publication: freeze edge additions, retargeting,
  and direct/prerequisite-side deletion after discovery while preserving whole-child cascades; include
  every edge mutation in claim generations; reject READY jobs with missing or non-successful prerequisites
  in both scheduler phases; and exact-compare dependency edges, prerequisite states, and relevant SQLite
  schema across publication hooks. Atomically roll back artifacts, hook data, and hook DDL when any fence
  fails. Add database-level success enforcement and adversarial edge/state/schema races.
- Publish all Build-Your-Own-X catalog entries through immutable content-v2 baselines and S2
  builder/reviewer bindings. Add exact, relocation-safe legacy retirement; active-worker deferral;
  strict malformed-history rollback; full-definition SQL guards; required canonical warehouse routing;
  and idempotent read-only repeats. Preserve provenance while quarantining four unverifiable pre-policy
  generic artifacts and KV-v1; replay the exact released KV-v2, HTTP, allocator, and bytecode profiles.
- Add durable runtime `retry_allowance` without removing `max_attempts` from S2 definition digests.
  Claims, retry/failure/lease recovery, graceful interruption, visibility, and BYOX remediation authority
  use the effective budget. Successful later attempts require the minimal controller-authorized allowance;
  an executed attempt-3 builder receives a `REVISE` independent review whose exact evidence is accepted
  as authority to seed a repair, not as candidate acceptance.

- Harden BYOX remediation ingestion around one bounded descriptor-pinned snapshot primitive. Review
  documents and their `tree-sha256-v2` digest now come from the same reads, builder archives are
  independently recomputed, directory scans stop at their remaining budget or first extra sentinel, and
  an end-of-pass name/inode/root revalidation rejects namespace and checksum sandwiches. Require exact
  status-string/label agreement, semantic profile labels, the canonical reviewer payload, gate/builder
  dependency set, candidate mappings, protected root, staged artifact identity/type/checksum/algorithm/
  attempt, and a catalog-anchored generic or finite specialized builder identity before publishing repair
  work. Generic builders must additionally match every catalog-derived job-spec field and one of the
  two complete released payload encodings (the original model-only execution policy or the current
  controller-added backend policy); the reviewer expectation is rebuilt from that canonical payload,
  never the mutable stored row. Load, normalize, filter, bound, and rebuild active-catalog snapshots
  behind the same `BEGIN IMMEDIATE` lock that publishes remediation work, closing the stale-snapshot
  interleaving window. Generic builders, completed repair builders, and all reviewers must also have a
  controller-reachable terminal state: canonical retry ceiling, integer current attempt within it,
  ordered finite timestamps, cleared lease/retry/failure ownership, and no cancellation; artifact and
  validation evidence remain bound to that attempt. This is checked before a repair reviewer or later
  generation can be published and again while validating a repair review. Reviewers additionally retain
  exact `codex_task`, examiner, `gpt-5.6-sol`, and `ultra` identities. Artifact paths must resolve through
  that pinned chain below
  `Database.path.parent / "artifacts"`; matching outside-host trees are not evidence. Document why a
  transient rename/restoration of the same pinned shared-ancestor inode is safe. Strict stored JSON now
  accepts only exact built-in text/bytes, applies deterministic lexical nesting/token/node/string/number
  limits independent of mutable interpreter integer settings, and rejects unpaired surrogates recursively
  in object keys and values.
- Centralize the five released specialized BYOX builder definitions (KV v1/v2, HTTP, allocator, and
  bytecode) in deterministic constructors shared by their original seed functions and remediation.
  Specialized review authorization now reconstructs the complete active-catalog-bound job definition and
  requires exact job/type/worker/payload/priority/score/retry ceiling/model/reasoning/dependencies plus a
  controller-reachable successful state. The constructors preserve the audited historical envelopes,
  including KV's three attempts, null model/reasoning, and its version dependency. Persisted legacy
  payloads remain untyped; only a fresh reviewer-facing copy receives the verified artifact type.
- Default the scheduler to holding legacy host-command validators, including command-mode review
  acceptance, while continuing to claim structural work. Malformed validator envelopes fail closed;
  held jobs remain untouched in `READY`, and CLI status reports the exact held count. Repeat the fence
  over every handler's actual validators immediately before execution so dynamically generated commands
  block without spawning a validator process. Replace the bootstrap backend gate's command comparison
  with deterministic input-integrity hashing so a fresh installation cannot deadlock on its own fence;
  bind that gate's validation and archive to a controller-installed fresh-inode cutover as well.
- Generalize the fresh-inode BYOX cutover to every ordinary structural challenge pack. Retained worker
  descriptors can mutate only the retired tree; post-validation, projected candidate, and prepared
  archive checksums must match the cutover record. Reject executable validators in this structural path,
  external hard links, unsafe absolute ancestors, and over-depth trees while preserving exact depth-limit
  parity between capture, copy, and checksum.
- Make BYOX repair publication operate on an authoritative fresh snapshot: copy selected outputs and
  protected staged inputs once through no-follow descriptors into new inodes, retain undeclared roots
  only as bounded quarantine evidence, reject cross-set hard links and rebinding, atomically retire the
  worker-visible tree before validation, and require cutover/projection/input/archive checksums to agree.
  Reconstruct the exact four staged inputs and combined read-only validation-workspace checksum during
  remediation replay, bind declared inventory paths/kinds to descriptor-pinned artifact bytes, and require
  the duplicated cutover record to agree. Preserve only seven identified pre-cutover attempt-1 artifacts
  by immutable artifact/job/checksum/attempt identity; reject every other missing or contradictory record.
- Centralize current and deployed-legacy backend gate definitions as frozen whole specifications. Before
  any remediation publication, require exact static job state, canonical workspace/heartbeat/timestamps,
  current-attempt PASS evidence and label support, and either the singleton current artifact manifest or
  the exact known deployed three-file legacy manifest. Authenticate base-review successor history against
  enumerated released payloads and temporally ordered terminal envelopes, and require every builder/review
  artifact to occupy its unique controller-defined semantic destination.
- Fence legacy and current catalog-scale BYOX/CSDIY Codex jobs at the runtime launch seam: require
  `exec`, `factory-isolated`, `gpt-5.6-sol`, `ultra`, and the exact authenticated non-WebSocket ARM
  provider route through independent payload/ID/artifact recognition without rewriting queued legacy
  payloads. Persist the exact payload policy on newly seeded catalog and course-progression jobs, cover
  BYOX repair builders, identity-bind the two historical partial-policy exceptions, and reject malformed
  or conflicting declarations and effective route settings.
- Add a bounded, deterministic `revalidate-byox-code` command and migration-backed append-only ledger
  for replaying archived BYOX packs through the current structural code-presence gate. Bind exact
  artifact/job/attempt/checksum/policy evidence, evaluate a pure gate over a V2-checksum-bound immutable
  manifest captured through a private no-follow copy, preserve conflicting observations, fail closed on
  drift and unsafe trees, and never infer `BUILDS` or `TESTED`. Pin every root and nested traversal with
  descriptor-relative no-follow opens, and stop resumably at aggregate artifact, byte, or wall budgets
  without recording an unevaluated artifact as failed. Charge every hash/copy read even for rejected
  trees, enforce expiry at the SQLite append boundary, and preserve budget exhaustion if scratch cleanup
  also fails.
- Add migration-backed start-time reproducibility records for every new run: deterministic
  code/configuration/job-policy/invocation digests, Git commit plus bounded tracked/untracked worktree
  evidence, secret-free actual Codex argv/model/reasoning and effective leaf-prompt fingerprints, a
  mode-`0600` `RUN_PROVENANCE.json`, operator event, CLI inspection, and artifact linkage.
- Raise the operated scheduler ceiling from the initial three-job probe to 12 concurrent claims, with
  limits of five reference builders, two course managers, two students, and three examiners; keep a
  continuous `run --until-idle` controller active to refill eligible slots.
- Replace the legacy Codex `--sandbox` option for new jobs with a fail-closed `factory-isolated`
  permission profile: root denied, workspace-only writes, minimal and exact toolchain reads, tool
  network off, no inherited environment, auth storage hidden, and hosted/MCP/browser/plugin/subagent
  surfaces disabled. Record the beta runner and incomplete `/proc` assurance explicitly.
- Add deterministic BYOX review verdict semantics. `PASS`, `REVISE`, and `FAIL` are all preserved review
  outcomes, but none can mint `REVIEWED` or count as workflow acceptance. A separate fail-closed
  `review_acceptance` command validator must provide captured external evidence. Seed idempotent,
  provenance-linked v2 remediation jobs for attempted v1 reviews that lack the current contract.
- Reject exact controller-environment credentials in canonical job payloads before SQLite persistence,
  including JSON-escaped values, without storing or identifying the credential. Reject backend endpoint
  URLs containing user information, queries, fragments, control characters, or non-HTTP schemes.
- Add `seed-course-next`, a bounded, idempotent CSDIY continuation refiller that selects one normalized
  resource record per eligible course only after current verified independent-examiner PASS evidence.
  Every result explicitly declines course-completion and transfer-verification claims.
- Recover an exact failed legacy course-materializer contract while preserving its first run and
  validation failures, and supersede one exact unstarted cancelled legacy graph with deterministic v2
  successor IDs while leaving all terminal rows, descendants, and reservation evidence immutable.
- Route standalone `codex exec --json` through the verified ARM custom provider base
  `https://openai-api-proxy.geo.arm.com/api/providers/openai/v1` using the Responses transport,
  WebSockets disabled, `gpt-5.6-sol`, and `ultra` reasoning; record the effective profile per run.
- Reuse Codex authentication without embedding credentials in factory configuration or artifacts, and
  validate the route with a bounded exact-output backend gate. Retain older `blocked_authentication`
  rows as historical evidence requiring deliberate manual retry, not as a current provider outage.
- Pre-S2 history: seed complete graph coverage for all 359 active Build-Your-Own-X projects (355 generic builders plus
  four existing specialized builders, each with a reviewer) and all 82 active CSDIY kickoff cohorts
  (manager, target-learner student, and examiner). Coverage records scheduled work, not completion.
- Pre-S2 history: externally validate the MIT 6.824 course-manager artifact. Preserve a generic Docker-in-Bash builder's
  first-attempt validation failure caused by a root `.git`, do not promote that failed tree, and retry
  the builder under the corrected contract. Preserve two completed legacy reviews without counting them
  as accepted in the absence of deterministic verdict evidence.
- Preserve immutable source-snapshot history while exposing only the active commit
  to catalog synthesis, seeding, planning, reporting, and generated exercises.
- Publish scheduled source ingestion atomically with its validated artifact and
  fenced job success; cancelled, crashed, or rolled-back attempts leave no catalog rows.
- Stage artifacts beside their final destination, fsync the tree, use a same-filesystem rename and
  framed `tree-sha256-v2` checksum, then publish artifact evidence and job success transactionally.
- Verify published v2 artifacts at scheduler startup and logically quarantine missing or mismatched
  trees as `LEGACY_UNVERIFIED`/`PARTIAL`; preserve legacy v1 evidence without staging it downstream.
- Make scheduler shutdown exception-safe, including child reaping and bounded redacted stream drain
  after unexpected controller failures.
- Make unchanged source observations idempotent and document the required
  `init -> ingest -> run -> seed-all -> run` bootstrap ordering.
- Document the remaining hard-kill orphan-process boundary instead of treating lease
  recovery as operating-system process containment.
- Keep same-UID and beta-runner limitations explicit even after enforcing the stronger Codex permission
  profile; require a separately administered container or VM for hostile code or secrets.
- Add gated allocator, bytecode/interpreter, bounded HTTP, and durable event-service generators with
  architecture alternatives, hidden validation, debugging/review work, and measured benchmarks.
- Publish the allocator, bytecode VM, and event-service packs through the durable scheduler, retaining
  the initial managed-workspace integration failures and successful retry evidence.
- Materialize sealed-free learner views for all published deep project packs.
- Record the factory Git revision and tracked-worktree state in newly published artifact metadata.
- Add independent prepublication adversarial review; discovered contract, allocator-topology,
  language-semantics, HTTP-lifecycle, and event-lease defects now have regressions.

## 0.1.0 - 2026-08-30

- Bootstrapped the deterministic SQLite control plane, Codex backend abstraction, source adapters,
  worker isolation, validation, observability, and initial vertical-slice generators.
