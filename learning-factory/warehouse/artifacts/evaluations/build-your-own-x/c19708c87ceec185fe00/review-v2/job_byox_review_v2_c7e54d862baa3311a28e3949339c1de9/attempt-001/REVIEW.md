# Independent review

Verdict: **REVISE**. The pack has a strong teaching structure and unusually candid production caveats, but several stated protocol/resource invariants are not implemented and the documented validation path is incomplete. No candidate file was modified.

## Prioritized findings

### P1 — `read_timeout` is not a total read bound

`REQUIREMENTS.md:38-41` requires read time to be bounded. The blocking implementations call `settimeout(read_timeout)` once and then repeatedly call `recv` (`sealed/shared/http_core.py:350-367`), so every fragment arriving just before the inactivity timeout starts another wait. The selector implementation likewise updates `last_activity` after every read (`sealed/alternatives/event_loop/http_service.py:106-120,167-170`). A slow drip can therefore occupy a worker/connection far beyond the configured deadline, up to the byte bound.

The supplied slow-client probe sends one incomplete header and becomes completely idle. It proves recovery after inactivity only, not the documented total read-time property. Track an absolute per-request header/body deadline (and specify whether progress may extend it), then test a client that drips bytes just inside the inactivity interval against all architectures.

### P1 — malformed request bytes cross the claimed strict parser boundary

The request-target check only requires a leading slash and no `#`; header values reject NUL, CR, and LF but permit other control bytes (`sealed/shared/http_core.py:128-151`). An independent probe observed:

```text
ACCEPTED target-NUL: target='/\x00' host='x'
ACCEPTED host-CTL: target='/' host='x\x01y'
```

Those are not valid origin-form/header field bytes and are dangerous examples for a parser-focused exercise. Validate the request-target grammar and reject all disallowed control bytes before constructing `Request`; add deterministic cases alongside the existing ambiguity tests.

### P1 — increment escapes the documented integer bound

Operands are limited to `abs(number) <= 10**12` in `_payload`, but the result at `http_core.py:268-275` is stored without a checked addition. The independent probe returned:

```text
put_status=201 increment_status=200 resulting_value=1000000000001
```

This contradicts `REQUIREMENTS.md:30` and makes the storage bound unenforced. Define the allowed result range, reject overflow deterministically without mutation, and cover both positive and negative boundaries plus idempotent retries of a rejected operation.

### P1 — the advertised validation and production paths are absent

`README.md:40-46` directs learners/reviewers to `python3 scripts/run_all.py` and `production/PRODUCTIONIZATION.md`; `README.md:57` also advertises `production/`. None exists. The run-all command exits 2 with `No such file or directory`. This breaks the one documented way to reproduce the full evidence set and hides the promised operations material. Restore those submitted artifacts or remove/correct every claim and provide explicit bounded commands for each check.

### P2 — archived benchmark data is internally consistent but not attributable validation evidence

`benchmarks/results/smoke.json` contains 40 raw sequential and burst samples for each architecture; its medians, p95s, and request-rate arithmetic recompute correctly. It does not record an execution time, artifact/code hash, exact command, validator identity, provenance reference, or explicit validation label. `PROVENANCE.json` only says the file is measured after execution, which is builder prose and cannot establish that execution.

Keep the useful raw data and interpretation boundary, but bind generated results to the artifact revision and harness-controlled run record. The fresh benchmark was inconclusive here because the sandbox denied socket creation, so `BENCHMARKED` is not independently established.

### P2 — generated content has provenance metadata but no reuse license

`PROVENANCE.json` clearly distinguishes catalog metadata, source-derived facts, generated material, and the outbound tutorial boundary. That is good provenance hygiene. However, its CC0-1.0 field describes the catalog source; the candidate has no `LICENSE`, `COPYING`, `NOTICE`, or per-file grant for the newly generated code and prose. A source license does not by itself state the terms for separately generated material. Add an explicit license for the candidate and preserve any required upstream notices. External source identity/license and the no-copy assertion could not be independently checked in this restricted workspace.

### P2 — progressive disclosure depends on an unverified manual copy

Solutions, expected reviews, and reference tests are sensibly placed below `sealed/`, and `README.md:25-27` honestly calls this a human reveal boundary. The delivered tree nevertheless co-locates all answers and tells an operator to manually copy an allowlist; there is no deterministic student-view artifact or leakage check. Provide a harness-controlled export/manifest that includes only learner documents, `starter/`, and `public_tests/`, with a test proving no sealed/reference paths enter the learner view.

## What works well

- The manifest does not claim production readiness and treats validation labels as conditional targets.
- Requirements, concepts, design prompts, alternatives, and production caveats give learners meaningful engineering context rather than only route code.
- Under CPython 3.11.5, all 16 Python files compile; three pure public tests and five sealed parser contract tests pass.
- The fixed-seed parser probe completed 2000 iterations, while the debugging exercise gives a reproducible failing negative control and a passing corrected regression.
- The cache-review exercise demonstrates the exact cross-principal failure described by its sealed expected review.

Network correctness remains unverified because this review sandbox rejects AF_INET socket creation. Those checks are limitations, not candidate failures.
