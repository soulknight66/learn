# Changelog

## Unreleased

- Harden the quarantined validator sandbox after independent adversarial review: require proven real
  cgroup memory/pids limits with zero swap; deny VSOCK and all but Unix/IPv4/IPv6 sockets; deny memfd
  and SysV SHM; mask PID 1; close namespace FDs; distinguish signals through an immutable supervisor;
  detect mount crossings by mount ID; bind directory modes into v3 tree hashes; replace blanket `/usr`
  with an exact runtime; reject loader controls; and expand fail-closed secret handling. The ARM host's
  undelegated controllers are reported honestly as `BLOCKED`.
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
