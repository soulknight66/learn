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
bootstrap is therefore:

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
