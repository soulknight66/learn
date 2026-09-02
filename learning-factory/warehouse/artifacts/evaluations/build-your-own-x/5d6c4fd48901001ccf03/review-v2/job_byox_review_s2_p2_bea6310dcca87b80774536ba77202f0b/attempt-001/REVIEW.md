# Independent review

Verdict: **REVISE**.

The submission is unusually candid and mostly well constructed as a teaching pack. Its claimed
unit and writable-root smoke results were independently reproducible, the namespace path is opt-in,
and the manifest correctly remains `GENERATED` + `PARTIAL`. One acceptance-contract defect and a
weak provenance integrity check should be corrected before an advisory pass. This verdict does not
publish or authorize a `REVIEWED` label.

## Prioritized findings

### P1 — Registry accepts timestamps outside RFC 3339

R4 requires caller timestamps to be RFC 3339. `sealed/reference/minictr/registry.py:59` delegates to
`datetime.fromisoformat`, whose accepted language is broader. Through `Registry.create`, the
independent probe successfully stored all of these:

```text
2026-W01-1T03:04:05+00:00
20260102T030405+00:00
2026-01-02Q03:04:05+00:00
```

They use an ISO week date, basic date/time syntax, or a non-`T` separator and are not RFC 3339 date
times. This contradicts the public contract and weakens the format of durable evidence. Add a strict
RFC-3339 lexical check before parsing, including explicit timezone syntax, and cover the same cases
through `create`, `claim_start`, and `finish`. The existing test only rejects a timezone-less value.

### P2 — The stated provenance binding does not bind the provenance document

`MANIFEST.yaml` names `f7190e...ca5a` as `provenance_sha256`; that value equals the self-reported
`PROVENANCE.json.snapshot_sha256`, while the SHA-256 of the provenance file is
`1b00a5...5b611`. `environment/verify_pack.py:73-78` only compares those two embedded fields, so
changes to license classification, upstream URL, source metadata, or other provenance content can
still pass the advertised binding check.

If this field is intentionally a source-snapshot identifier, document or rename it and add a
separate digest for the canonical provenance document. Otherwise, store and verify the actual file
digest. The project/source/commit identities themselves were internally consistent.

### P2 — Learner quick-start commands select an incompatible interpreter here

The top-level and starter instructions invoke bare `python3`, which resolves to Python 3.6.8 in the
allocated environment and fails at import with `future feature annotations is not defined`. The
long-form validation record honestly gives the working Python 3.11.5 path, so this is not a false
test claim, but the primary learner route is not directly reproducible on the supplied host. Add a
3.11 preflight/version check or consistently show a configurable 3.11 interpreter in quick-start
commands.

### P3 — The public green suite gives no checkpoint for the learner-owned stages

All 10 public tests pass against the untouched starter even though planner, registry, runner, and
child setup still contain `NotImplementedError` or stage TODOs. The documentation discloses this and
asks learners to write tests, but a green initial run provides no executable progress signal for the
core stages. Public happy-path/interface tests for stages 3–5 could preserve hidden adversarial cases
while giving learners deterministic checkpoints.

## Verified strengths

- Under Python 3.11.5, the public suite passed 10/10, the sealed reference suite passed 24 active
  tests with one opt-in skip, and the adversarial suite passed 4/4.
- The opt-in writable-root `/bin/true` namespace smoke test passed on Linux 4.18/util-linux 2.32.1.
- An actually simultaneous two-connection SQLite claim had one winner; the transition trigger
  rejected `RUNNING -> CREATED`; an actual subprocess timed out, received group kill, and returned
  `timed_out=true` with exit code `-9`.
- Shell-free argv construction, bounded setup input, minimal helper environment, component-aware
  path checks, immutable mappings, and durable failed-state fields agree with the documented scope.
- The concepts, design questions, debugging reproducer, review exercise, sealed answers, tradeoffs,
  and production-gap analysis form a coherent staged learning route.
- The license boundary does not imply permission from the linked `NOASSERTION` tutorial and says
  that its URL is provenance only. No credential-like material, symlink, special entry, bytecode, or
  unexpected nested answer directory was found by the available checks.
- Validation claims are appropriately narrow: no `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`,
  `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is asserted.

## Review limitations and acceptance dependencies

The upstream catalog snapshot and linked tutorial were not present and network access was
unavailable, so originality and external license evidence could not be independently compared. The
review workspace contains the complete evaluator pack, not a rendered student view. `AGENTS.md` and
directory layout express progressive disclosure, but prose is not an access boundary; the
orchestrator must separately prove that `sealed/`, `adversarial/`, evaluator debugging answers,
review answers, and reference tests never enter a learner view.

The NFS workspace independently reproduced the disclosed default read-only remount failure
(`EPERM`, child exit 126). Only a writable-root benign workload was integration-tested. Hostile
containment, output bounds, PID-1 behavior, crash reconciliation, other kernels/filesystems,
fuzzing, controlled benchmarking, and transfer verification remain unproven and are correctly not
claimed.
