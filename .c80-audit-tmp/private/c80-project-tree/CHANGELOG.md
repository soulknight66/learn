# Changelog

## Unreleased

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
  recovery, and leave old-attempt removal to control-plane-confirmed retention.
  Stream and preflight student/dependency trees under shared entry/file/byte/depth limits, fail before
  retaining or reading entry 4,097, reject external hard links and rename races, and propagate only rwx
  mode bits through controller-owned copies.
  Reconcile detached descendants, require duplicate-free schema-valid JSON, publish neither file on any
  rejected envelope, globally cancel every ownerless claimable legacy examiner without a submission
  binding, and request cancellation for active ones while preserving attempt and terminal history.
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
  Preserve historical attempts with no cutover records while rejecting partial or contradictory records.
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
- Seed complete graph coverage for all 359 active Build-Your-Own-X projects (355 generic builders plus
  four existing specialized builders, each with a reviewer) and all 82 active CSDIY kickoff cohorts
  (manager, target-learner student, and examiner). Coverage records scheduled work, not completion.
- Externally validate the MIT 6.824 course-manager artifact. Preserve a generic Docker-in-Bash builder's
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
