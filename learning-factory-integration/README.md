# Learning Factory

Learning Factory is a local, restart-safe system that turns public CS curricula and build-from-scratch
tutorial catalogs into validated, progressively revealable learning artifacts.

The product is the corpus under `warehouse/`; the scheduler exists to build that corpus reliably.
SQLite is authoritative for state. Workers receive isolated attempt directories, and deterministic
validators—not worker assertions—decide completion.

## Quick start

```bash
export PYTHONPATH="$PWD/src"
python3 -m learnfactory init
python3 -m learnfactory ingest ../cs-self-learning ../build-your-own-x
python3 -m learnfactory run --until-idle
python3 -m learnfactory seed-all
python3 -m learnfactory status
python3 -m learnfactory run --until-idle
python3 -m learnfactory seed-course-next --max-courses 10
python3 -m unittest discover -s tests -v
```

Use `python3 -m learnfactory --help` for job inspection, retries, reports, and exercise commands.
The enabled backend is the installed `codex exec --json` interface routed through the verified ARM
provider at `https://openai-api-proxy.geo.arm.com/api/providers/openai/v1`. It uses the Responses
transport with WebSockets disabled and defaults to `gpt-5.6-sol` with `ultra` reasoning. Credentials
come from Codex's supported authentication store; they are never embedded in factory configuration,
job payloads, prompts, or documentation. Deterministic fake and local handlers support testing without
model calls, and effective model/reasoning values are recorded per run.

Every new run also records a start-time `learnfactory-run-provenance-v3` fingerprint. It binds the
execution-relevant tracked and non-ignored untracked code tree, allowlisted parsed configuration,
job-policy payload, and the secret-free Codex argv/model/reasoning/effective-prompt envelope. Exact
byte hashes are used for credential-free values; detected credential-bearing fields are redacted before
hashing and explicitly labeled as a `safe-redacted-envelope` rather than falsely claiming exactness. The full
human-readable record is stored as `RUN_PROVENANCE.json` beside the run logs and linked from SQLite and
published artifact metadata; prompt, payload, source-file, environment, and credential contents are not
copied into it.

The operated scheduler has a global ceiling of 12 concurrent jobs, further bounded to five reference
builders, two course managers, two students, and three examiners (with separate lower limits for other
roles). A continuous `run --until-idle` controller is active at this checkpoint. An earlier
`--max-jobs 3` invocation was a deliberately bounded probe: `--max-jobs` limits total dispatches by that
controller invocation, not the factory's configured concurrent capacity.

New Codex invocations use the named `factory-isolated` permission profile rather than the legacy
`--sandbox` flag. The profile denies the filesystem root, grants write access only to the job workspace,
allows only Codex's minimal runtime plus explicitly configured toolchain reads, disables worker-tool
network access, starts with no inherited environment, hides Codex authentication storage, and disables
hosted, MCP, browser, plugin, and subagent surfaces. This is a tested and materially stronger local
boundary, but the Codex Linux permission-profile runner is beta and its `/proc` deny should not be
treated as a formally complete hostile multi-tenant boundary; see `SECURITY.md`.

The first run publishes the normalized source catalogs. Seeding deliberately comes
after that publication so course and project jobs can bind to immutable provenance.

## Operated corpus and queued graph

As of 2026-08-31, the active normalized catalogs contain 82 CSDIY courses and 359 Build Your Own X
entries. The durable scale-out graph covers every entry:

- 82 bounded CSDIY kickoff cohorts, each with a course manager, persistent `student-target` attempt,
  and independent examiner job;
- 359 immutable, baseline-scoped S2 BYOX builder/reviewer pairs; previously validated specialized
  implementations remain historical evidence rather than substituting for an S2 definition; and
- one externally validated backend-capability gate ahead of newly scheduled Codex work.

These counts describe catalog coverage and queued work, not course or project completion. The bounded
course pipelines can be extended one normalized resource at a time with `seed-course-next`, but only
after the prior independent examiner has published a verified PASS. A nonpassing kickoff first receives
fresh checksum-bound student/examiner revisions under the configured finite limit; neither a revision
nor a later unit PASS is a whole-course claim. Even exhaustion of normalized records is explicitly not
whole-course or transfer completion. A pre-S2 generic builder for “Docker implemented in around 100
lines of bash” failed external validation after creating a forbidden root `.git` directory; that failed
attempt remains historical evidence and was never promoted, but it is not the current S2 graph.

BYOX review completion and candidate acceptance are now separate facts. Versioned deterministic
`review_verdict` contract v2 records exactly `PASS`, `REVISE`, or `FAIL` and rejects empty, non-string,
or untrimmed evidence/check entries without launching a command. All three outcomes preserve a review
artifact, and none can mint `REVIEWED`. Seeded reviewers carry a closed, non-executable acceptance gate;
only a separately configured external acceptance policy can bind exact candidate/review artifacts and
mint `REVIEWED`. S2 definitions are immutable and baseline-bound. Cutover retires only exact queued
legacy definitions, defers while an exact legacy worker is active, and preserves all terminal history;
it never rewrites a bound definition in place.

Deep, progressively revealable packs currently include:

- [caller-owned-arena C allocator](warehouse/artifacts/projects/systems/caller-owned-arena-c-allocator/job_project_allocator_vertical_v1/attempt-002/README.md), with three tested architectures, corruption/debugging work, and measured benchmarks;
- [Sprig bytecode VM](warehouse/artifacts/projects/languages/sprig-bytecode-vm/job_project_bytecode_vertical_v1/attempt-002/README.md), with tree-walk and bytecode engines, differential fuzzing, and review exercises;
- [durable event-processing service](warehouse/artifacts/projects/production-services/durable-event-processing-service/job_project_event_service_vertical_v1/attempt-001/README.md), covering leases, fencing, idempotency, crash recovery, dead letters, and operations;
- [bounded HTTP counter service](warehouse/artifacts/projects/networking/bounded-http-counter-service/job_project_http_service_vertical_v1/attempt-001/README.md), with three concurrency architectures and lifecycle testing;
- [durable bytes KV store](warehouse/artifacts/projects/database/durable-bytes-kv/job_project_kvstore_vertical_v2/attempt-001/README.md); and
- [copy-on-write transfer lab](warehouse/artifacts/courses/mit-6-s081/cow-transfer/job_course_mit6s081_vertical_v2/attempt-001/README.md).

Learner-safe copies live under `warehouse/learners/student-target/exercises/`; these
contain starter material and public tests but omit sealed references, hidden tests,
and expected reviews. See [the current checkpoint](reports/latest.md) and
[the human catalog](warehouse/catalog/README.md) for navigation.

Earlier default-endpoint attempts remain durably recorded as `blocked_authentication`; those historical
states are not evidence that the verified ARM route is currently unavailable. They are never reset
automatically. Retry them deliberately after inspecting their attempt history and dependencies; see
`OPERATIONS.md`.

Validated artifact trees are fsynced in same-filesystem staging before atomic rename. Artifact evidence,
source activation, and fenced job success then publish in one SQLite transaction. Scheduler startup
rechecks framed v2 checksums and marks inconsistent records `LEGACY_UNVERIFIED`/`PARTIAL` rather than
continuing to trust them. This closes ordinary crash/restart paths but does not make SQLite and the
filesystem one transaction.

## Data boundary

Only the two configured public source repositories and files explicitly staged into a job workspace
are inputs. The factory does not scan neighboring repositories. Student views omit `sealed/` and are
checked for escaping symlinks; new Codex jobs additionally execute under the fail-closed permission
profile summarized above. See `SECURITY.md` for the current isolation boundary and limitations.
